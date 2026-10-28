package io.github.oli97430.becquee

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.util.Log
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.Executors
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit

/** Source d'images : caméra du téléphone ou fichier vidéo (analyse a posteriori, test). */
interface Source {
    val fichier: Boolean
    val fps: Double
    /** Image suivante, ou null en fin de fichier / à l'arrêt. */
    fun lire(): Trame?
    fun fermer() {}
}

/** Vidéo lue image par image ; l'instant de chaque image est son numéro / fps (comme sur le PC). */
class SourceFichier(context: Context, uri: Uri) : Source {
    private val mmr = MediaMetadataRetriever().apply {
        if (uri.scheme == "file") setDataSource(uri.path) else setDataSource(context, uri)
    }
    val nbImages = mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT)?.toInt() ?: 0
    private val dureeMs = mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: 0L
    override val fichier = true
    override val fps = if (dureeMs > 0 && nbImages > 0) (nbImages * 1000.0 / dureeMs).let { if (it in 1.0..120.0) it else 15.0 } else 15.0
    private var suivante = 0
    private val lot = ArrayDeque<Trame>()

    override fun lire(): Trame? {
        if (lot.isEmpty()) {
            if (suivante >= nbImages) return null
            val n = minOf(30, nbImages - suivante)
            val images = mmr.getFramesAtIndex(suivante, n)
            if (suivante == 0) Log.i("Becquee", "video ${mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)}x" +
                "${mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)} rotation " +
                "${mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)} image ${images[0].width}x${images[0].height}")
            for ((k, b) in images.withIndex()) lot.add(Images.depuisBitmap(b, ((suivante + k) * 1e6 / fps).toLong()))
            suivante += n
        }
        return lot.removeFirstOrNull()
    }

    override fun fermer() = mmr.release()
}

/** Images poussées par CameraX ; la plus ancienne est abandonnée si le moteur prend du retard. */
class SourceCamera : Source {
    override val fichier = false
    override val fps = 15.0
    private val file = ArrayBlockingQueue<Trame>(3)
    @Volatile var ouverte = true

    fun pousser(t: Trame) {
        if (!file.offer(t)) { file.poll(); file.offer(t) }
    }

    override fun lire(): Trame? {
        while (ouverte) file.poll(200, TimeUnit.MILLISECONDS)?.let { return it }
        return null
    }

    override fun fermer() { ouverte = false }
}

/** Ce que l'écran affiche à chaque image. */
data class Vue(
    val boite: Boite? = null, val oiseaux: List<Boite> = emptyList(), val enregistrement: Boolean = false,
    val etiquette: String = "", val fps: Double = 0.0, val duree: Double = 0.0, val largeur: Int = 0, val hauteur: Int = 0,
)

private class Image420(val donnees: ByteArray, val tempsUs: Long)

/** Un clip en cours, avec les avis du reconnaisseur sur les images analysées. */
private class Visite(dossier: File, fps: Int, largeur: Int, hauteur: Int, avant: List<Image420>, private val micro: Micro?) {
    val debut = Date()
    val base: String = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss", Locale.US).format(debut).let { b ->
        var n = b
        var i = 2
        while (File(dossier, "$n.jpg").exists() || dossier.listFiles { f -> f.name.startsWith("${n}_") }?.isNotEmpty() == true) n = "${b}_${i++}"
        n
    }
    val video = File(dossier, "${base}_en_cours.mp4")
    val enregistreur = Enregistreur(video, largeur, hauteur, fps, micro?.frequence)
    private var dernierSonUs = Long.MIN_VALUE
    val scores = mutableMapOf<String, MutableList<Float>>()
    val premiers = mutableMapOf<String, Int>()          // nb d'analyses où l'espèce arrive en tête
    var meilleure: Triple<Float, Trame, Boite?>? = null  // (confiance, image, oiseau recadré)
    var oiseauxVus = 0f                                  // analyses où un oiseau a été détecté
    var photoOiseau: Triple<Float, Trame, Boite>? = null // meilleure image avec oiseau (si pas de reconnaissance)
    var premierUs = -1L
    var dernierUs = -1L
    var nbImages = 0

    init { avant.forEach { ecrire(it) }; ecrireSon() }

    /** Son entendu depuis le dernier morceau écrit (le premier appel reprend les secondes d'avant). */
    fun ecrireSon() {
        val m = micro ?: return
        for (morceau in m.depuis(dernierSonUs)) {
            enregistreur.ecrireAudio(morceau.pcm, morceau.tempsUs)
            dernierSonUs = morceau.tempsUs
        }
    }

    fun ecrire(i: Image420) {
        enregistreur.ecrire(i.donnees, i.tempsUs)
        if (premierUs < 0) premierUs = i.tempsUs
        dernierUs = i.tempsUs
        nbImages++
    }

    fun ajouterPrediction(predictions: List<Pair<String, Float>>, t: Trame, recadrage: Boite?) {
        for ((e, s) in predictions) scores.getOrPut(e) { mutableListOf() }.add(s)
        val (espece, score) = predictions[0]
        premiers[espece] = (premiers[espece] ?: 0) + 1
        if (score > (meilleure?.first ?: 0f)) meilleure = Triple(score, t, recadrage)
    }

    /** Espèce déjà sûre (4 fois en tête, à 90 % au moins, sans concurrente) : inutile de la reconnaître
     *  encore ; le détecteur continue de suivre l'oiseau pour la durée de la visite et la photo. */
    fun especeSure() = premiers.size == 1 && premiers.values.first() >= 4 && (scores[premiers.keys.first()]?.max() ?: 0f) >= 0.9f

    /** Espèce retenue = vote sur toute la visite : elle doit arriver en tête sur au moins la moitié
     *  des analyses et atteindre le seuil au moins une fois. */
    fun conclure(seuil: Float): Pair<String, Float> {
        ecrireSon()
        enregistreur.terminer()
        if (scores.isEmpty()) return INCONNU to 0f
        val espece = scores.maxBy { it.value.sum() }.key
        val confiance = scores[espece]!!.max()
        val majoritaire = (premiers[espece] ?: 0) >= premiers.values.sum() / 2.0
        return (if (majoritaire && confiance >= seuil) espece else INCONNU) to confiance
    }
}

/** Résultat d'une analyse (détecteur d'oiseaux + reconnaissance) sur une image de la visite. */
private class Analyse(val visite: Visite, val trame: Trame, val oiseaux: List<Pair<Float, Boite>>, val confirmation: Float,
                      val predictions: List<Pair<String, Float>>?, val recadrage: Boite?)

/**
 * Boucle caméra -> mouvement -> enregistrement -> filtre oiseau -> reconnaissance, portée de
 * Surveillance.executer() (mangeoire_cam.py). Avec un fichier, l'analyse est faite image par image
 * (résultat identique à chaque passage) ; avec la caméra, les réseaux de neurones tournent à côté
 * pour que le clip reste fluide pendant qu'ils réfléchissent.
 */
class Surveillance(
    private val context: Context,
    private val source: Source,
    private val dossier: File,
    private val reconnaisseur: Reconnaisseur,
    private val detecteurOiseaux: DetecteurOiseaux,
    var seuil: Float = 0.75f,
    var surface: Float = 0.01f,
    private val avant: Double = 3.0,
    private val apres: Double = 4.0,
    private val dureeMax: Double = 120.0,
    private val analyseToutes: Double = 0.5,
    var filtreOiseaux: Boolean = true,
    private val garderSansOiseau: Boolean = false,
    private val menageJours: Int = 60,
    private val menageGo: Float = 10f,
    private val micro: Micro? = null,
    private val surImage: (Trame, Vue) -> Unit = { _, _ -> },
    private val surVisite: (Map<String, String>) -> Unit = {},
    private val surMessage: (String) -> Unit = {},
) {
    private val seuilOiseauBioclip = 0.85f
    @Volatile private var arret = false
    private val journal = Journal(dossier)
    private val calcul = Executors.newSingleThreadExecutor()

    fun arreter() { arret = true; source.fermer() }

    private fun message(texte: String) {
        Log.i("Becquee", texte)
        surMessage(texte)
    }

    private var nbAnalyses = 0
    private var dureeAnalyses = 0L
    private var dureeDetecteur = 0L

    private fun analyser(visite: Visite, t: Trame, boite: Boite?): Analyse {
        val debut = System.nanoTime()
        return analyser1(visite, t, boite).also {
            // temps moyen d'une analyse (détecteur + BioCLIP), noté toutes les 20 analyses
            dureeAnalyses += System.nanoTime() - debut
            if (++nbAnalyses % 20 == 0) Log.i("Becquee", "analyse : ${dureeAnalyses / nbAnalyses / 1_000_000} ms en moyenne " +
                "dont détecteur ${dureeDetecteur / nbAnalyses / 1_000_000} ms ($nbAnalyses)")
        }
    }

    private fun analyser1(visite: Visite, t: Trame, boite: Boite?): Analyse {
        var oiseaux = emptyList<Pair<Float, Boite>>()
        var confirmation = 1f
        val cible: Boite?
        if (filtreOiseaux) {
            val d = System.nanoTime()
            oiseaux = detecteurOiseaux.detecter(t)
            dureeDetecteur += System.nanoTime() - d
            if (oiseaux.isEmpty() && boite != null && boite.l * boite.h <= 0.5f * t.largeur * t.hauteur) {
                // le détecteur rate certains oiseaux (pose, contre-jour...) : BioCLIP juge la zone en
                // mouvement ; il faut deux avis sûrs pour valider une visite. Une zone plus grande que la
                // moitié de l'image (changement de lumière, écran qui défile, téléphone bougé) n'est pas un
                // oiseau posé : BioCLIP s'y trompait sur une page de texte
                val p = reconnaisseur.probOiseau(t, Images.recadrer(t.largeur, t.hauteur, boite, 0.2f))
                if (p >= seuilOiseauBioclip) { oiseaux = listOf(p to boite); confirmation = 0.5f }
            }
            cible = oiseaux.firstOrNull()?.second
        } else cible = boite
        if (cible == null || visite.especeSure()) return Analyse(visite, t, oiseaux, confirmation, null, null)
        val recadrage = Images.recadrer(t.largeur, t.hauteur, cible)
        return Analyse(visite, t, oiseaux, confirmation, reconnaisseur.classer(t, recadrage), recadrage)
    }

    fun executer(): Boolean {
        dossier.mkdirs()
        // clips d'une session interrompue (appli tuée) : illisibles, effacés
        dossier.listFiles { f -> f.name.endsWith("_en_cours.mp4") }?.forEach { it.delete() }
        menage()
        Rangement.construireGalerie(dossier)
        message(context.getString(R.string.chargement_modeles))
        reconnaisseur.charger()
        detecteurOiseaux.charger()
        // caméra : mouvement cherché sur une image de 320 pixels (au lieu de 480 pour un fichier, comme sur
        // le PC) pour laisser le processeur aux réseaux de neurones qui tournent en même temps
        val detecteur = DetecteurMouvement(surface, if (source.fichier) 480 else 320)
        val tampon = ArrayDeque<Image420>()
        var visite: Visite? = null
        var dernierMouvement = 0.0
        var derniereAnalyse = 0.0
        var demarrage = -1.0
        var etiquette = ""
        var oiseaux = emptyList<Pair<Float, Boite>>()
        var enCours: Future<Analyse>? = null
        var tFps = System.nanoTime()
        var nFps = 0
        var fpsMesure = 0.0
        var largeur = 0
        var hauteur = 0

        fun terminer() {
            enCours?.cancel(false)
            enCours = null
            visite?.let { terminerVisite(it, source.fps) }
            visite = null
            etiquette = ""
            oiseaux = emptyList()
        }

        fun appliquer(a: Analyse, maintenant: Double) {
            val v = visite
            if (v == null || a.visite !== v) return               // visite déjà terminée
            oiseaux = a.oiseaux
            if (a.oiseaux.isNotEmpty()) {
                v.oiseauxVus += a.confirmation
                dernierMouvement = maintenant                    // un oiseau immobile prolonge la visite
                val (score, b) = a.oiseaux[0]
                if (score > (v.photoOiseau?.first ?: 0f)) v.photoOiseau = Triple(score, a.trame, Images.recadrer(a.trame.largeur, a.trame.hauteur, b))
            }
            if (a.predictions != null) {
                v.ajouterPrediction(a.predictions, a.trame, a.recadrage)
                etiquette = "${afficher(a.predictions[0].first)}  ${(a.predictions[0].second * 100).toInt()} %"
            }
        }

        try {
            while (!arret) {
                var t = source.lire() ?: break
                if (largeur == 0) {
                    largeur = t.largeur and 1.inv()
                    hauteur = t.hauteur and 1.inv()
                    message(context.getString(R.string.source_ouverte, largeur, hauteur, source.fps.toInt()))
                }
                if (t.largeur != largeur || t.hauteur != hauteur) t = recadrerPair(t, largeur, hauteur) ?: continue
                val maintenant = t.tempsUs / 1e6
                if (demarrage < 0) demarrage = maintenant
                detecteur.surfaceMin = surface
                var boite = detecteur.analyser(t)
                if (maintenant - demarrage < 3) boite = null    // le modèle de fond apprend la scène

                if (boite != null) {
                    dernierMouvement = maintenant
                    if (visite == null) {
                        visite = Visite(dossier, source.fps.toInt(), largeur, hauteur, tampon.toList(), micro)
                        tampon.clear()
                        message(context.getString(R.string.debut_enregistrement))
                    }
                }

                val v = visite
                if (v != null) {
                    v.ecrire(Image420(Images.versI420(t), t.tempsUs))
                    v.ecrireSon()
                    enCours?.let { f -> if (f.isDone) { enCours = null; runCatching { f.get() }.getOrNull()?.let { appliquer(it, maintenant) } } }
                    if (enCours == null && maintenant - derniereAnalyse >= analyseToutes && (boite != null || oiseaux.isNotEmpty())) {
                        derniereAnalyse = maintenant
                        val b = boite
                        if (source.fichier) appliquer(analyser(v, t, b), maintenant)
                        else enCours = calcul.submit<Analyse> { analyser(v, t, b) }
                    }
                    val duree = (v.dernierUs - v.premierUs) / 1e6
                    if (maintenant - dernierMouvement > apres || duree > dureeMax) terminer()
                } else {
                    tampon.addLast(Image420(Images.versI420(t), t.tempsUs))
                    while (tampon.isNotEmpty() && maintenant - tampon.first().tempsUs / 1e6 > avant) tampon.removeFirst()
                }

                nFps++
                val ecoule = (System.nanoTime() - tFps) / 1e9
                if (ecoule >= 1) { fpsMesure = nFps / ecoule; tFps = System.nanoTime(); nFps = 0 }
                surImage(t, Vue(boite, oiseaux.map { it.second }, visite != null, etiquette, fpsMesure,
                    visite?.let { (it.dernierUs - it.premierUs) / 1e6 } ?: 0.0, t.largeur, t.hauteur))
            }
        } finally {
            terminer()
            source.fermer()
            calcul.shutdown()
        }
        return largeur > 0
    }

    /** Image d'une autre taille (rotation de l'appareil...) : coupée ou ignorée, l'encodeur a une taille fixe. */
    private fun recadrerPair(t: Trame, l: Int, h: Int): Trame? {
        if (t.largeur < l || t.hauteur < h) return null
        val p = IntArray(l * h)
        for (y in 0 until h) System.arraycopy(t.pixels, y * t.largeur, p, y * l, l)
        return Trame(p, l, h, t.tempsUs)
    }

    private fun afficher(espece: String) = when (espece) {
        INCONNU -> context.getString(R.string.inconnu)
        PAS_UN_OISEAU -> context.getString(R.string.pas_un_oiseau)
        else -> espece
    }

    private fun terminerVisite(visite: Visite, fps: Double) {
        val duree = if (source.fichier) visite.nbImages / fps else (visite.dernierUs - visite.premierUs) / 1e6 + 1 / fps
        val (espece, confiance) = visite.conclure(seuil)

        // « Pas un oiseau » : appris de vos corrections (feuilles, écureuil, reflet...)
        val sansOiseau = (filtreOiseaux && visite.oiseauxVus < 1) || espece == PAS_UN_OISEAU
        if (sansOiseau && !garderSansOiseau) {
            visite.video.delete()
            message(context.getString(R.string.sans_oiseau, duree.toInt()))
            return
        }
        val nom = "${visite.base}_${nomFichier(espece)}"
        val video = File(dossier, "$nom.mp4")
        visite.video.renameTo(video)
        val photo = visite.meilleure?.let { it.second to it.third } ?: visite.photoOiseau?.let { it.second to it.third }
        var fichierPhoto = ""
        if (photo != null) {
            fichierPhoto = "$nom.jpg"
            Images.enregistrerJpeg(photo.first.bitmap(), File(dossier, fichierPhoto))
            photo.second?.let { Images.enregistrerJpeg(Images.extraire(photo.first, it), File(dossier, "${nom}_oiseau.jpg")) }
        }
        val ligne = mapOf(
            "date" to SimpleDateFormat("yyyy-MM-dd", Locale.US).format(visite.debut),
            "heure" to SimpleDateFormat("HH:mm:ss", Locale.US).format(visite.debut),
            "duree_s" to String.format(Locale.US, "%.0f", duree), "espece" to espece,
            "confiance" to String.format(Locale.US, "%.2f", confiance), "video" to video.name, "photo" to fichierPhoto,
            "source" to if (espece != INCONNU) "image" else "", "chants" to "", "corrige" to "",
        )
        journal.ajouter(ligne)
        Rangement.garderDansGalerie(dossier, ligne)
        message(context.getString(R.string.fin_visite, afficher(espece), (confiance * 100).toInt(), duree.toInt()))
        surVisite(ligne)
        menage()
    }

    private fun menage() {
        val n = Rangement.nettoyer(dossier, menageJours, menageGo)
        if (n > 0) message(context.getString(R.string.menage, n))
    }
}
