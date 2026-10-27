package io.github.oli97430.becquee

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.net.Uri
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.resolutionselector.AspectRatioStrategy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import kotlinx.coroutines.flow.MutableStateFlow
import java.io.File
import java.util.concurrent.Executors

/** État partagé entre le moteur (service) et l'écran. */
object Etat {
    val image = MutableStateFlow<Bitmap?>(null)
    val vue = MutableStateFlow(Vue())
    val messages = MutableStateFlow<List<String>>(emptyList())
    /** null = arrêté, sinon "camera" ou "fichier". */
    val marche = MutableStateFlow<String?>(null)
    val versionJournal = MutableStateFlow(0)
    @Volatile var surveillance: Surveillance? = null
    @Volatile var reconnaisseur: Reconnaisseur? = null

    fun message(texte: String) {
        messages.value = (messages.value + texte).takeLast(30)
    }
}

fun dossierVisites(context: Context) = File(context.getExternalFilesDir(null) ?: context.filesDir, "visites")

/**
 * Service au premier plan : la surveillance continue écran éteint ou appli en arrière-plan.
 * Actions : camera, fichier (data = vidéo), arreter.
 */
class SurveillanceService : LifecycleService() {
    companion object {
        const val CAMERA = "camera"
        const val FICHIER = "fichier"
        const val ARRETER = "arreter"

        fun lancer(context: Context, action: String, video: Uri? = null) {
            val i = Intent(context, SurveillanceService::class.java).setAction(action).setData(video)
            if (action == ARRETER) context.startService(i) else ContextCompat.startForegroundService(context, i)
        }
    }

    private var camera: ProcessCameraProvider? = null
    private val executeur = Executors.newSingleThreadExecutor()

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            ARRETER -> { Etat.surveillance?.arreter(); return START_NOT_STICKY }
            CAMERA, FICHIER -> if (Etat.marche.value == null) demarrer(intent.action!!, intent.data)
        }
        return START_NOT_STICKY
    }

    private fun notification(): Notification {
        val gestion = getSystemService(NotificationManager::class.java)
        gestion.createNotificationChannel(NotificationChannel("surveillance", getString(R.string.app_name), NotificationManager.IMPORTANCE_LOW))
        val ouvrir = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, "surveillance")
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(getString(R.string.notification_surveillance))
            .setContentIntent(ouvrir)
            .setOngoing(true)
            .build()
    }

    private fun demarrer(action: String, video: Uri?) {
        val type = if (action == CAMERA) ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA else ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
        startForeground(1, notification(), type)
        Etat.marche.value = action
        val reglages = Reglages(this)
        val source: Source = try {
            if (action == CAMERA) SourceCamera().also { ouvrirCamera(it) } else SourceFichier(this, video!!)
        } catch (e: Exception) {
            android.util.Log.e("Becquee", "source", e)
            Etat.message(getString(R.string.source_erreur, e.javaClass.simpleName))
            arreterService()
            return
        }
        val dossier = dossierVisites(this)
        val reconnaisseur = Etat.reconnaisseur?.takeIf { reglages.memePosition(it) }
            ?: Reconnaisseur(this, reglages.latitude, reglages.longitude, File(dossier, "corrections"), Etat::message)
                .also { reglages.retenir(it) }
        Etat.reconnaisseur = reconnaisseur
        val s = Surveillance(
            this, source, dossier, reconnaisseur, DetecteurOiseaux(this),
            seuil = reglages.seuil, surface = reglages.surface, filtreOiseaux = reglages.filtreOiseaux,
            surImage = { t, vue ->
                // l'écran n'a pas besoin de toutes les images
                if (Etat.image.value == null || vue.enregistrement || (t.tempsUs / 66_000) % 2 == 0L) Etat.image.value = t.bitmap()
                Etat.vue.value = vue
            },
            surVisite = { Etat.versionJournal.value++ },
            surMessage = Etat::message,
        )
        Etat.surveillance = s
        Thread {
            try {
                s.executer()
                if (action == FICHIER) Etat.message(getString(R.string.analyse_terminee))
            } catch (e: Throwable) {
                android.util.Log.e("Becquee", "moteur", e)
                Etat.message(getString(R.string.source_erreur, e.javaClass.simpleName + ": " + e.message))
            } finally {
                Etat.surveillance = null
                android.os.Handler(mainLooper).post { arreterService() }
            }
        }.apply { name = "surveillance" }.start()
    }

    private fun ouvrirCamera(source: SourceCamera) {
        val fournisseur = ProcessCameraProvider.getInstance(this).get()
        camera = fournisseur
        val analyse = ImageAnalysis.Builder()
            .setResolutionSelector(ResolutionSelector.Builder()
                .setAspectRatioStrategy(AspectRatioStrategy.RATIO_4_3_FALLBACK_AUTO_STRATEGY)
                .setResolutionStrategy(ResolutionStrategy(Size(640, 480), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER))
                .build())
            .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
        analyse.setAnalyzer(executeur) { image ->
            try {
                val plan = image.planes[0]
                val w = image.width
                val h = image.height
                val buf = plan.buffer
                val pixels = IntArray(w * h)
                for (y in 0 until h) {
                    var o = y * plan.rowStride
                    for (x in 0 until w) {
                        val r = buf.get(o).toInt() and 0xFF
                        val g = buf.get(o + 1).toInt() and 0xFF
                        val b = buf.get(o + 2).toInt() and 0xFF
                        pixels[y * w + x] = (0xFF shl 24) or (r shl 16) or (g shl 8) or b
                        o += plan.pixelStride
                    }
                }
                source.pousser(Images.tourner(Trame(pixels, w, h, image.imageInfo.timestamp / 1000), image.imageInfo.rotationDegrees))
            } finally {
                image.close()
            }
        }
        fournisseur.unbindAll()
        fournisseur.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, analyse)
    }

    private fun arreterService() {
        camera?.unbindAll()
        camera = null
        Etat.marche.value = null
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        Etat.surveillance?.arreter()
        executeur.shutdown()
        super.onDestroy()
    }
}
