package io.github.oli97430.becquee

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File

/**
 * Clip MP4 (H.264) d'une visite. L'encodeur n'est démarré qu'au début d'une visite : entre deux
 * visites, seules les 3 dernières secondes sont gardées en mémoire (images YUV), ce qui épargne la
 * batterie par rapport à un encodage permanent.
 */
class Enregistreur(fichier: File, private val largeur: Int, private val hauteur: Int, fps: Int) {
    private val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
    private val muxer = MediaMuxer(fichier.path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
    private val info = MediaCodec.BufferInfo()
    private var piste = -1
    private var t0 = -1L
    private var dernier = -1L

    init {
        val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, largeur, hauteur).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
            setInteger(MediaFormat.KEY_BIT_RATE, (largeur * hauteur * fps * 0.2).toInt().coerceAtLeast(500_000))
            setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        }
        codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        codec.start()
    }

    /** Ajoute une image YUV 4:2:0 planaire (I420) à l'instant tempsUs. */
    fun ecrire(i420: ByteArray, tempsUs: Long) {
        if (t0 < 0) t0 = tempsUs
        val pts = maxOf(tempsUs - t0, dernier + 1)        // instants strictement croissants
        dernier = pts
        while (true) {
            val i = codec.dequeueInputBuffer(10_000)
            if (i >= 0) {
                remplir(codec.getInputImage(i)!!, i420)
                codec.queueInputBuffer(i, 0, largeur * hauteur * 3 / 2, pts, 0)
                break
            }
            vider(false)
        }
        vider(false)
    }

    private fun remplir(image: android.media.Image, i420: ByteArray) {
        val plans = image.planes
        val tailles = listOf(Triple(0, largeur, hauteur), Triple(largeur * hauteur, largeur / 2, hauteur / 2),
            Triple(largeur * hauteur * 5 / 4, largeur / 2, hauteur / 2))
        for ((k, t) in tailles.withIndex()) {
            val (debut, w, h) = t
            val plan = plans[k]
            val buf = plan.buffer
            val pas = plan.pixelStride
            val ligne = plan.rowStride
            for (y in 0 until h) {
                if (pas == 1) {
                    buf.position(y * ligne)
                    buf.put(i420, debut + y * w, w)
                } else {
                    for (x in 0 until w) buf.put(y * ligne + x * pas, i420[debut + y * w + x])
                }
            }
        }
    }

    private fun vider(fin: Boolean) {
        var attentes = 0
        while (true) {
            val i = codec.dequeueOutputBuffer(info, if (fin) 10_000 else 0)
            when {
                i == MediaCodec.INFO_TRY_AGAIN_LATER -> if (!fin || ++attentes > 300) return
                i == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    piste = muxer.addTrack(codec.outputFormat)
                    muxer.start()
                }
                i >= 0 -> {
                    val b = codec.getOutputBuffer(i)!!
                    if (info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) info.size = 0
                    if (info.size > 0 && piste >= 0) {
                        b.position(info.offset)
                        b.limit(info.offset + info.size)
                        muxer.writeSampleData(piste, b, info)
                    }
                    codec.releaseOutputBuffer(i, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) return
                }
            }
        }
    }

    fun terminer() {
        try {
            val i = codec.dequeueInputBuffer(100_000)
            if (i >= 0) codec.queueInputBuffer(i, 0, 0, dernier + 1, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
            vider(true)
        } finally {
            codec.stop()
            codec.release()
            if (piste >= 0) muxer.stop()
            muxer.release()
        }
    }
}
