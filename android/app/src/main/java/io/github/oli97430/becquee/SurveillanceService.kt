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
import android.os.SystemClock
import android.util.Size
import android.view.OrientationEventListener
import android.view.Surface
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
    @Volatile var dernierAffichage = 0L

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
        /** Test du mode caméra sans caméra : la vidéo est envoyée au moteur image par image, en temps réel. */
        const val SIMULATION = "simulation"

        fun lancer(context: Context, action: String, video: Uri? = null) {
            val i = Intent(context, SurveillanceService::class.java).setAction(action).setData(video)
            if (action == ARRETER) context.startService(i) else ContextCompat.startForegroundService(context, i)
        }
    }

    private var camera: ProcessCameraProvider? = null
    private var orientation: OrientationEventListener? = null
    private val executeur = Executors.newSingleThreadExecutor()

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            ARRETER -> { Etat.surveillance?.arreter(); return START_NOT_STICKY }
            CAMERA, FICHIER, SIMULATION -> if (Etat.marche.value == null) demarrer(intent.action!!, intent.data)
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
        val reglages = Reglages(this)
        Modeles.acceleration = reglages.acceleration
        Modeles.fils = reglages.fils
        // son des clips : seulement avec la caméra, si l'utilisateur l'a permis
        val avecSon = action == CAMERA && reglages.son &&
            ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED
        val type = when {
            action != CAMERA -> ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            avecSon -> ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            else -> ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA
        }
        startForeground(1, notification(), type)
        Etat.marche.value = action
        val micro = if (avecSon) runCatching { Micro() }.getOrNull() else null
        val source: Source = try {
            when (action) {
                CAMERA -> SourceCamera().also { ouvrirCamera(it) }
                SIMULATION -> SourceCamera().also { simuler(it, SourceFichier(this, video!!)) }
                else -> SourceFichier(this, video!!)
            }
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
            menageJours = reglages.menageJours, menageGo = reglages.menageGo, micro = micro,
            surImage = { t, vue ->
                // l'écran n'est mis à jour que s'il est affiché, environ 8 fois par seconde
                if (Etat.image.value == null || (Etat.image.subscriptionCount.value > 0 && (t.tempsUs / 125_000) != (Etat.dernierAffichage / 125_000))) {
                    Etat.dernierAffichage = t.tempsUs
                    Etat.image.value = t.bitmap()
                }
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
                micro?.arreter()
                Etat.surveillance = null
                android.os.Handler(mainLooper).post { arreterService() }
            }
        }.apply { name = "surveillance" }.start()
    }

    /** Pousse les images de la vidéo comme le ferait CameraX : au rythme de la vidéo, la plus ancienne
     *  abandonnée si le moteur prend du retard, horodatées à l'arrivée. Fin de vidéo = arrêt. */
    private fun simuler(source: SourceCamera, video: SourceFichier) {
        Thread {
            val debut = SystemClock.elapsedRealtime()
            var n = 0
            while (source.ouverte) {
                val t = video.lire() ?: break
                val attente = debut + (n++ * 1000 / video.fps).toLong() - SystemClock.elapsedRealtime()
                if (attente > 0) Thread.sleep(attente)
                source.pousser(Trame(t.pixels, t.largeur, t.hauteur, SystemClock.elapsedRealtimeNanos() / 1000))
            }
            video.fermer()
            Thread.sleep(6000)      // laisser la dernière visite se terminer
            source.fermer()
        }.apply { name = "simulation" }.start()
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
            .setTargetRotation(Surface.ROTATION_90)
            .build()
        // images toujours en largeur (640x480, comme les modèles l'attendent), à l'endroit selon le côté
        // où le téléphone est couché ; tenu en hauteur, l'image reste en largeur (taille fixe du clip)
        orientation = object : OrientationEventListener(this) {
            override fun onOrientationChanged(o: Int) {
                when (o) {
                    in 60..120 -> analyse.targetRotation = Surface.ROTATION_270
                    in 240..300 -> analyse.targetRotation = Surface.ROTATION_90
                }
            }
        }.apply { if (canDetectOrientation()) enable() }
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
                // horloge commune avec le micro : l'instant d'arrivée de l'image
                source.pousser(Images.tourner(Trame(pixels, w, h, SystemClock.elapsedRealtimeNanos() / 1000), image.imageInfo.rotationDegrees))
            } finally {
                image.close()
            }
        }
        fournisseur.unbindAll()
        fournisseur.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, analyse)
    }

    private fun arreterService() {
        orientation?.disable()
        orientation = null
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
