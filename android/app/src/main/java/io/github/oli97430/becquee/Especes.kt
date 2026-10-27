package io.github.oli97430.becquee

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.text.Normalizer
import java.util.Locale

/** Espèce candidate : nom scientifique, nom dans la langue de l'appli, nom anglais, nb d'observations. */
data class Espece(val sci: String, val nom: String, val en: String, val obs: Int)

const val PAS_UN_OISEAU = "Pas un oiseau"
const val INCONNU = "Inconnu"
private val NON_OISEAUX = listOf("human", "engine", "noise", "gun", "siren", "dog", "fireworks", "power tools")

fun sansAccents(texte: String): String =
    Normalizer.normalize(texte, Normalizer.Form.NFKD).replace(Regex("[^\\p{ASCII}]"), "")

/** Clé de comparaison tolérante (accents, tirets, casse) : « Rouge-gorge » == « Rougegorge ». */
fun cleEspece(nom: String) = sansAccents(nom).lowercase().filter { it.isLetterOrDigit() }

fun nomFichier(texte: String) = sansAccents(texte).map { if (it.isLetterOrDigit()) it else '_' }.joinToString("").trim('_')

object Especes {
    /** Langue de l'appli parmi celles de Becquée (fr, en, es, de, pt, it). */
    fun langue(): String = Locale.getDefault().language.takeIf { it in listOf("fr", "en", "es", "de", "pt", "it") } ?: "en"

    private fun localeInaturalist() = if (langue() == "pt") "pt-BR" else langue()

    /** Étiquettes BirdNET : (nom scientifique, nom anglais, nom dans la langue). */
    fun etiquettesBirdnet(context: Context): List<Triple<String, String, String>> {
        val lignes = Modeles.texte(context, "BirdNET_GLOBAL_6K_V2.4_Labels.txt").lines().filter { it.isNotBlank() }
        val suffixe = mapOf("fr" to "fr", "es" to "es", "de" to "de", "pt" to "pt_BR", "it" to "it")[langue()]
        var noms = if (suffixe == null) emptyList() else runCatching {
            Modeles.texte(context, "BirdNET_GLOBAL_6K_V2.4_Labels_$suffixe.txt").lines().filter { it.isNotBlank() }
                .map { it.substringAfter("_") }
        }.getOrDefault(emptyList())
        if (noms.size != lignes.size) noms = lignes.map { it.substringAfter("_") }
        return lignes.zip(noms) { l, n -> Triple(l.substringBefore("_"), l.substringAfter("_"), n) }
    }

    /**
     * Espèces d'oiseaux observées autour de la position (iNaturalist, observations validées), des plus
     * courantes aux plus rares. Cache de 30 jours. Sans réseau : dernier cache, sinon le méta-modèle
     * géographique de BirdNET ; sans position : toutes les espèces BirdNET.
     */
    fun locales(context: Context, latitude: Double?, longitude: Double?, message: (String) -> Unit): List<Espece> {
        if (latitude == null || longitude == null) return birdnet(context, null, null)
        val cache = File(context.filesDir, String.format(Locale.US, "especes_%.2f_%.2f_%s.json", latitude, longitude, langue()))
        if (cache.exists() && System.currentTimeMillis() - cache.lastModified() < 30L * 86400 * 1000)
            return completerNoms(context, lire(cache))
        return try {
            var especes = emptyList<Espece>()
            var rayon = 0
            for (r in listOf(50, 200, 1000)) {            // élargir dans les régions peu observées
                rayon = r
                especes = inaturalist(latitude, longitude, r)
                if (especes.size >= 40) break
            }
            if (especes.isEmpty()) throw IllegalStateException("aucune observation")
            cache.writeText(JSONArray(especes.map {
                JSONObject().put("sci", it.sci).put("nom", it.nom).put("en", it.en).put("obs", it.obs)
            }).toString())
            message(context.getString(R.string.especes_locales, especes.size, rayon))
            completerNoms(context, especes)
        } catch (e: Exception) {
            if (cache.exists()) return completerNoms(context, lire(cache))
            message(context.getString(R.string.especes_hors_ligne, e.javaClass.simpleName))
            birdnet(context, latitude, longitude)
        }
    }

    private fun lire(f: File): List<Espece> {
        val a = JSONArray(f.readText())
        return (0 until a.length()).map { a.getJSONObject(it) }
            .map { Espece(it.getString("sci"), it.getString("nom"), it.optString("en"), it.optInt("obs")) }
    }

    private fun inaturalist(latitude: Double, longitude: Double, rayon: Int): List<Espece> {
        val q = listOf("lat" to latitude, "lng" to longitude, "radius" to rayon, "taxon_id" to 3,
            "quality_grade" to "research", "rank" to "species", "per_page" to 500, "locale" to localeInaturalist())
            .joinToString("&") { (k, v) -> "$k=" + URLEncoder.encode(v.toString(), "UTF-8") }
        val c = URL("https://api.inaturalist.org/v1/observations/species_counts?$q").openConnection() as HttpURLConnection
        c.setRequestProperty("User-Agent", "Becquee/1.0 (mangeoire connectee, Android)")
        c.connectTimeout = 15000
        c.readTimeout = 30000
        val resultats = c.inputStream.use { JSONObject(it.readBytes().toString(Charsets.UTF_8)) }.getJSONArray("results")
        return (0 until resultats.length()).map { resultats.getJSONObject(it) }.map { r ->
            val t = r.getJSONObject("taxon")
            val nom = t.optString("preferred_common_name").ifEmpty { t.getString("name") }
            Espece(t.getString("name"), nom.replaceFirstChar { it.uppercase() }, t.optString("english_common_name"), r.getInt("count"))
        }
    }

    /** Sans nom commun iNaturalist dans la langue : nom BirdNET traduit, puis nom anglais. */
    private fun completerNoms(context: Context, especes: List<Espece>): List<Espece> {
        if (especes.none { it.nom == it.sci }) return especes
        val birdnet = etiquettesBirdnet(context).filter { it.second != it.third || langue() == "en" }.associate { it.first to it.third }
        return especes.map { if (it.nom == it.sci) it.copy(nom = birdnet[it.sci] ?: it.en.ifEmpty { it.sci }) else it }
    }

    /** Liste de secours : espèces BirdNET plausibles sur l'année à cette position (toutes sans position). */
    fun birdnet(context: Context, latitude: Double?, longitude: Double?): List<Espece> {
        val etiquettes = etiquettesBirdnet(context)
        var gardees: List<Int> = etiquettes.indices.toList()
        if (latitude != null && longitude != null) runCatching {
            val session = Modeles.session(context, "birdnet_data_model.onnx")
            val x = FloatArray(48 * 3) { i -> when (i % 3) { 0 -> latitude.toFloat(); 1 -> longitude.toFloat(); else -> (i / 3 + 1).toFloat() } }
            val p = Modeles.executer(session, x, longArrayOf(48, 3))[0]
            session.close()
            val n = etiquettes.size
            gardees = etiquettes.indices.filter { j -> (0 until 48).any { s -> p[s * n + j] >= 0.03f } }
        }
        return gardees.map { etiquettes[it] }.filter { e -> NON_OISEAUX.none { e.first.lowercase().contains(it) } }
            .map { Espece(it.first, it.third, it.second, 0) }
    }
}
