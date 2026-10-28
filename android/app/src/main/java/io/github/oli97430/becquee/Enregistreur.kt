package io.github.oli97430.becquee

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Clip MP4 d'une visite : image H.264 et, si le micro est actif, son AAC. Les encodeurs ne sont
 * démarrés qu'au début d'une visite : entre deux visites, seules les 3 dernières secondes sont
 * gardées en mémoire (images YUV, son brut), ce qui épargne la batterie.
 */
class Enregistreur(fichier: File, private val largeur: Int, private val hauteur: Int, fps: Int, frequenceAudio: Int? = null) {
    private val muxer = MediaMuxer(fichier.path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
    private val video = Piste(MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC))
    private val audio = frequenceAudio?.let { Piste(MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)) }
    private var demarre = false
    // échantillons sortis avant que le muxer connaisse toutes ses pistes
    private val enAttente = mutableListOf<Triple<Piste, ByteArray, MediaCodec.BufferInfo>>()
    private var t0 = -1L

    private inner class Piste(val codec: MediaCodec) {
        var index = -1
        var dernier = -1L
        val info = MediaCodec.BufferInfo()
    }

    init {
        video.codec.configure(MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, largeur, hauteur).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
            setInteger(MediaFormat.KEY_BIT_RATE, (largeur * hauteur * fps * 0.2).toInt().coerceAtLeast(500_000))
            setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        }, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        video.codec.start()
        if (audio != null && frequenceAudio != null) {
            audio.codec.configure(MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, frequenceAudio, 1).apply {
                setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
                setInteger(MediaFormat.KEY_BIT_RATE, 64_000)
                setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16_384)
            }, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            audio.codec.start()
        }
    }

    /** Ajoute une image YUV 4:2:0 planaire (I420) à l'instant tempsUs. */
    fun ecrire(i420: ByteArray, tempsUs: Long) {
        if (t0 < 0) t0 = tempsUs
        val pts = maxOf(tempsUs - t0, video.dernier + 1)        // instants strictement croissants
        video.dernier = pts
        while (true) {
            val i = video.codec.dequeueInputBuffer(10_000)
            if (i >= 0) {
                remplir(video.codec.getInputImage(i)!!, i420)
                video.codec.queueInputBuffer(i, 0, largeur * hauteur * 3 / 2, pts, 0)
                break
            }
            vider(video, false)
        }
        vider(video, false)
    }

    /** Ajoute un morceau de son (PCM 16 bits mono) commencé à l'instant tempsUs (même horloge que les images). */
    fun ecrireAudio(pcm: ShortArray, tempsUs: Long) {
        val a = audio ?: return
        if (t0 < 0 || tempsUs < t0) return                       // son d'avant la première image du clip
        val pts = maxOf(tempsUs - t0, a.dernier + 1)
        a.dernier = pts
        val octets = ByteBuffer.allocate(pcm.size * 2).order(ByteOrder.LITTLE_ENDIAN).apply { asShortBuffer().put(pcm) }.array()
        var debut = 0
        while (debut < octets.size) {
            val i = a.codec.dequeueInputBuffer(10_000)
            if (i < 0) { vider(a, false); continue }
            val b = a.codec.getInputBuffer(i)!!
            b.clear()
            val n = minOf(b.remaining(), octets.size - debut)
            b.put(octets, debut, n)
            a.codec.queueInputBuffer(i, 0, n, pts + debut / 2 * 1_000_000L / frequence(), 0)
            debut += n
        }
        vider(a, false)
    }

    private val frequenceSon = frequenceAudio ?: 44_100
    private fun frequence() = frequenceSon

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

    private fun vider(p: Piste, fin: Boolean) {
        var attentes = 0
        while (true) {
            val i = p.codec.dequeueOutputBuffer(p.info, if (fin) 10_000 else 0)
            when {
                i == MediaCodec.INFO_TRY_AGAIN_LATER -> if (!fin || ++attentes > 300) return
                i == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    p.index = muxer.addTrack(p.codec.outputFormat)
                    if (video.index >= 0 && (audio == null || audio.index >= 0)) {
                        muxer.start()
                        demarre = true
                        for ((piste, donnees, info) in enAttente) muxer.writeSampleData(piste.index, ByteBuffer.wrap(donnees), info)
                        enAttente.clear()
                    }
                }
                i >= 0 -> {
                    val b = p.codec.getOutputBuffer(i)!!
                    if (p.info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) p.info.size = 0
                    if (p.info.size > 0) {
                        b.position(p.info.offset)
                        b.limit(p.info.offset + p.info.size)
                        if (demarre) muxer.writeSampleData(p.index, b, p.info)
                        else {
                            val copie = ByteArray(p.info.size).also { b.get(it) }
                            val info = MediaCodec.BufferInfo().apply { set(0, p.info.size, p.info.presentationTimeUs, p.info.flags) }
                            enAttente.add(Triple(p, copie, info))
                        }
                    }
                    p.codec.releaseOutputBuffer(i, false)
                    if (p.info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) return
                }
            }
        }
    }

    fun terminer() {
        try {
            for (p in listOfNotNull(video, audio)) {
                val i = p.codec.dequeueInputBuffer(100_000)
                if (i >= 0) p.codec.queueInputBuffer(i, 0, 0, p.dernier + 1, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                vider(p, true)
            }
            // aucun son reçu (micro muet ou coupé) : le clip est gardé, en image seule
            if (!demarre && video.index >= 0) {
                muxer.start()
                demarre = true
                for ((piste, donnees, info) in enAttente) if (piste === video) muxer.writeSampleData(piste.index, ByteBuffer.wrap(donnees), info)
                enAttente.clear()
            }
        } finally {
            for (p in listOfNotNull(video, audio)) {
                runCatching { p.codec.stop() }
                p.codec.release()
            }
            if (demarre) muxer.stop()
            muxer.release()
        }
    }
}
