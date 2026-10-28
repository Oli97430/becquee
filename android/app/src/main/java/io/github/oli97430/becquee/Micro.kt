package io.github.oli97430.becquee

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.SystemClock

/**
 * Micro du téléphone en continu : les dernières secondes restent en mémoire, pour que le son d'une
 * visite commence avec ses 3 s d'avant, comme l'image. Même horloge que les images de la caméra
 * (SystemClock.elapsedRealtimeNanos).
 */
class Micro(val frequence: Int = 44_100) {
    class Morceau(val tempsUs: Long, val pcm: ShortArray)

    private val morceaux = ArrayDeque<Morceau>()
    @Volatile private var actif = true
    private val taille = 2048        // ~46 ms à 44,1 kHz

    @SuppressLint("MissingPermission")   // vérifiée par le service avant de créer le micro
    private val enregistrement = AudioRecord(
        MediaRecorder.AudioSource.CAMCORDER, frequence, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
        maxOf(AudioRecord.getMinBufferSize(frequence, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT), taille * 8),
    )

    private val fil = Thread {
        enregistrement.startRecording()
        while (actif) {
            val pcm = ShortArray(taille)
            val n = enregistrement.read(pcm, 0, taille)
            if (n <= 0) continue
            // l'instant du début du morceau : maintenant moins sa durée
            val t = SystemClock.elapsedRealtimeNanos() / 1000 - n * 1_000_000L / frequence
            synchronized(morceaux) {
                morceaux.addLast(Morceau(t, if (n == taille) pcm else pcm.copyOf(n)))
                while (morceaux.isNotEmpty() && t - morceaux.first().tempsUs > 8_000_000) morceaux.removeFirst()
            }
        }
        enregistrement.stop()
        enregistrement.release()
    }.apply { name = "micro"; start() }

    /** Morceaux commencés après l'instant tUs. */
    fun depuis(tUs: Long): List<Morceau> = synchronized(morceaux) { morceaux.filter { it.tempsUs > tUs } }

    fun arreter() { actif = false }
}
