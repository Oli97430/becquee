package io.github.oli97430.becquee

import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Ménage des vieux clips et galerie des plus belles photos, portés de mangeoire_cam.py
 * (nettoyer, garder_dans_galerie). La galerie et le journal ne sont jamais effacés.
 */
object Rangement {
    private const val GO = 1024L * 1024 * 1024

    /**
     * Efface les clips (mp4 + photos) plus vieux que `jours`, puis les plus anciens tant que le
     * dossier dépasse `maxGo` ou que le téléphone a moins de 1 Go libre. 0 = pas de limite.
     * Renvoie le nombre de clips effacés.
     */
    fun nettoyer(dossier: File, jours: Int, maxGo: Float): Int {
        var clips = (dossier.listFiles { f -> f.name.endsWith(".mp4") && !f.name.endsWith("_en_cours.mp4") } ?: return 0)
            .sortedBy { it.name }
        var supprimes = 0
        fun effacer(mp4: File) {
            val base = mp4.nameWithoutExtension
            listOf(mp4, File(dossier, "$base.jpg"), File(dossier, "${base}_oiseau.jpg")).forEach { it.delete() }
            supprimes++
        }
        if (jours > 0) {
            val limite = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date(System.currentTimeMillis() - jours * 86_400_000L))
            clips.filter { it.name.take(10) < limite }.forEach { effacer(it) }
            clips = clips.filter { it.exists() }
        }
        fun taille() = dossier.listFiles { f -> f.isFile && (f.name.endsWith(".mp4") || f.name.endsWith(".jpg")) }?.sumOf { it.length() } ?: 0L
        val clipsRestants = ArrayDeque(clips)
        if (maxGo > 0) {
            var t = taille()
            while (clipsRestants.isNotEmpty() && t > maxGo * GO) {
                val mp4 = clipsRestants.removeFirst()
                t -= mp4.length() + File(dossier, mp4.nameWithoutExtension + ".jpg").length()
                effacer(mp4)
            }
        }
        // téléphone presque plein : on garde au moins 1 Go libre pour le système et les nouveaux clips
        while (clipsRestants.size > 1 && dossier.usableSpace < GO) effacer(clipsRestants.removeFirst())
        return supprimes
    }

    // ------------------------------------------------------------------ galerie
    fun lireGalerie(dossier: File): JSONObject = runCatching {
        JSONObject(File(dossier, "galerie/galerie.json").readText())
    }.getOrDefault(JSONObject())

    private fun ecrireGalerie(dossier: File, index: JSONObject) {
        File(dossier, "galerie").mkdirs()
        File(dossier, "galerie/galerie.json").writeText(index.toString(1))
    }

    /** Copie la photo de la visite dans galerie/ si c'est la plus sûre de son espèce. */
    @Synchronized
    fun garderDansGalerie(dossier: File, ligne: Map<String, String>): Boolean {
        val espece = ligne["espece"].orEmpty()
        val photo = File(ligne["photo"].orEmpty()).name
        if (espece == INCONNU || espece == PAS_UN_OISEAU || photo.isEmpty() || !File(dossier, photo).exists()) return false
        val index = lireGalerie(dossier)
        val ancienne = index.optJSONObject(espece)
        val confiance = ligne["confiance"]?.toFloatOrNull() ?: 0f
        if (ancienne != null && (ancienne.optString("confiance").toFloatOrNull() ?: 0f) > confiance) return false
        val source = File(dossier, photo)
        val recadrage = File(dossier, source.nameWithoutExtension + "_oiseau.jpg")  // l'oiseau en gros plutôt que la scène
        val cible = "galerie/${nomFichier(espece)}.jpg"
        File(dossier, "galerie").mkdirs()
        (if (recadrage.exists()) recadrage else source).copyTo(File(dossier, cible), overwrite = true)
        index.put(espece, JSONObject().put("photo", cible).put("confiance", ligne["confiance"]).put("date", ligne["date"])
            .put("heure", ligne["heure"]).put("video", ligne["video"]))
        ecrireGalerie(dossier, index)
        return true
    }

    /** Après une correction : la photo quitte l'ancienne espèce ; vérifiée à la main, elle passe devant. */
    @Synchronized
    fun corrigerGalerie(dossier: File, ligne: Map<String, String>) {
        val index = lireGalerie(dossier)
        for (nom in index.keys().asSequence().toList()) {
            val e = index.getJSONObject(nom)
            if (e.optString("video") == ligne["video"] && nom != ligne["espece"]) {
                File(dossier, e.optString("photo")).delete()
                index.remove(nom)
            }
        }
        ecrireGalerie(dossier, index)
        garderDansGalerie(dossier, ligne + ("confiance" to "1.00"))
    }

    /** Première ouverture : la galerie est remplie avec les visites déjà notées. */
    fun construireGalerie(dossier: File) {
        if (File(dossier, "galerie/galerie.json").exists()) return
        Journal(dossier).lire().forEach { garderDansGalerie(dossier, it) }
    }
}
