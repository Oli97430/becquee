package io.github.oli97430.becquee

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer

/** Modèles livrés dans l'APK (assets/modeles), copiés une fois dans la mémoire de l'appli. */
object Modeles {
    // aucune donnée ne quitte le téléphone : télémétrie d'ONNX Runtime coupée
    val env: OrtEnvironment by lazy { OrtEnvironment.getEnvironment().apply { runCatching { setTelemetry(false) } } }

    fun fichier(context: Context, nom: String): File {
        val dossier = File(context.filesDir, "modeles").apply { mkdirs() }
        val f = File(dossier, nom)
        val taille = context.assets.openFd("modeles/$nom").use { it.length }
        // recopié après chaque mise à jour de l'appli (un modèle changé peut garder la même taille)
        val miseAJour = context.packageManager.getPackageInfo(context.packageName, 0).lastUpdateTime
        if (!f.exists() || f.length() != taille || f.lastModified() < miseAJour) {
            val tmp = File(dossier, "$nom.tmp")
            context.assets.open("modeles/$nom").use { e -> tmp.outputStream().use { e.copyTo(it, 1 shl 20) } }
            tmp.renameTo(f)
        }
        return f
    }

    fun texte(context: Context, nom: String): String =
        context.assets.open("modeles/$nom").use { it.readBytes().toString(Charsets.UTF_8) }

    /** Accélération des calculs : "cpu" (défaut), "xnnpack" ou "nnapi" (puce IA du téléphone). */
    @Volatile var acceleration = "cpu"
    @Volatile var fils = 4

    fun session(context: Context, nom: String): OrtSession {
        val options = OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(fils.coerceIn(1, Runtime.getRuntime().availableProcessors()))
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            runCatching {
                when (acceleration) {
                    "xnnpack" -> addXnnpack(mapOf("intra_op_num_threads" to fils.toString()))
                    "nnapi" -> addNnapi()
                }
            }.onFailure { android.util.Log.w("Becquee", "accélération $acceleration indisponible", it) }
        }
        return env.createSession(fichier(context, nom).absolutePath, options)
    }

    /** Matrice float16 (N x 512) écrite par convertir_modeles.py, lue en float32. */
    fun vecteursF16(context: Context, nom: String, dim: Int = 512): Array<FloatArray> {
        val octets = context.assets.open("modeles/$nom").use { it.readBytes() }
        val b = ByteBuffer.wrap(octets).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        return Array(b.limit() / dim) { i -> FloatArray(dim) { j -> demiVersFloat(b.get(i * dim + j)) } }
    }

    private fun demiVersFloat(h: Short): Float = android.util.Half.toFloat(h)

    fun executer(session: OrtSession, entree: FloatArray, forme: LongArray): Array<FloatArray> {
        OnnxTensor.createTensor(env, FloatBuffer.wrap(entree), forme).use { t ->
            session.run(mapOf(session.inputNames.first() to t)).use { r ->
                return Array(r.size()) { i ->
                    val v = r.get(i) as OnnxTensor
                    val fb = v.floatBuffer
                    FloatArray(fb.remaining()).also { fb.get(it) }
                }
            }
        }
    }
}
