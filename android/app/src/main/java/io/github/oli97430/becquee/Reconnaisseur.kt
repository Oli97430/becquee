package io.github.oli97430.becquee

import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.BitmapFactory
import java.io.File
import kotlin.math.exp
import kotlin.math.ln

/**
 * Espèce à partir d'une image d'oiseau recadrée, avec BioCLIP (zero-shot) : comme la version Windows,
 * mais l'encodeur de texte ne tourne pas sur le téléphone. Les vecteurs texte de toutes les espèces
 * d'oiseaux ont été calculés sur le PC (bioclip_textes.bin, un par nom scientifique).
 *
 * Candidats : les espèces locales + celles de vos corrections. Chaque photo de corrections/<espèce>/
 * devient un exemple ; une image qui ressemble beaucoup à un exemple corrigé tire la prédiction vers
 * son espèce (mémoire d'exemples, à la manière de Tip-Adapter).
 */
class Reconnaisseur(
    private val context: Context,
    private val latitude: Double?,
    private val longitude: Double?,
    private val dossierCorrections: File?,
    private val message: (String) -> Unit,
) {
    companion object {
        const val ALPHA = 20f            // poids de la mémoire d'exemples
        const val BETA = 6f              // finesse de la mémoire d'exemples
        const val MARGE = 8f             // handicap des classes sans description
        const val POIDS_A_PRIORI = 1f    // poids de la fréquence locale des espèces
        val MOYENNE = floatArrayOf(0.48145466f, 0.4578275f, 0.40821073f)
        val ECART = floatArrayOf(0.26862954f, 0.26130258f, 0.27577711f)
        const val NB_OISEAU = 2          // les 2 premières phrases de bioclip_oiseau.bin disent « oiseau »
    }

    private var session: OrtSession? = null
    private lateinit var table: Map<String, FloatArray>
    private lateinit var generique: FloatArray
    private lateinit var textesOiseau: Array<FloatArray>
    var especes: List<Espece> = emptyList(); private set
    var noms: List<String> = emptyList(); private set
    private var textesClasses: Array<FloatArray> = emptyArray()
    private var aPriori = FloatArray(0)
    private var sansTexte = IntArray(0)
    private var exemples: Array<FloatArray> = emptyArray()
    private var etiquettes = IntArray(0)

    @Synchronized
    fun charger() {
        if (session != null) return
        session = Modeles.session(context, "bioclip_image.onnx")
        val noms = Modeles.texte(context, "bioclip_textes.txt").lines().filter { it.isNotEmpty() }
        val vecteurs = Modeles.vecteursF16(context, "bioclip_textes.bin")
        table = noms.zip(vecteurs.toList()).toMap()
        generique = Modeles.vecteursF16(context, "bioclip_oiseau_generique.bin")[0]
        textesOiseau = Modeles.vecteursF16(context, "bioclip_oiseau.bin")
        especes = Especes.locales(context, latitude, longitude, message)
        apprendre()
    }

    private fun vecteurTexte(sci: String) = table[sci] ?: generique

    /** Vecteur texte d'une espèce ajoutée par correction (nom local, anglais ou scientifique). */
    private fun texteEspece(nom: String): FloatArray? {
        if (nom == PAS_UN_OISEAU) return null
        val cle = cleEspece(nom)
        for ((sci, en, local) in Especes.etiquettesBirdnet(context)) {
            if (cle == cleEspece(local) || cle == cleEspece(sci) || cle == cleEspece(en)) return vecteurTexte(sci)
        }
        table.keys.firstOrNull { cleEspece(it) == cle }?.let { return vecteurTexte(it) }
        return generique
    }

    fun vecteurImage(t: Trame, zone: Boite): FloatArray {
        val rgb = Images.redimensionnerRgb(t, zone.x, zone.y, zone.l, zone.h, 224, 224)
        return Modeles.executer(session!!, Images.tenseur(rgb, MOYENNE, ECART), longArrayOf(1, 3, 224, 224))[0]
    }

    private fun vecteurPhoto(f: File): FloatArray? {
        val b = BitmapFactory.decodeFile(f.path) ?: return null
        val t = Images.depuisBitmap(b, 0)
        return vecteurImage(t, Boite(0, 0, t.largeur, t.hauteur))
    }

    /** (Re)lit les photos .jpg de corrections/<espèce>/. Renvoie (nb de photos, nb d'espèces). */
    @Synchronized
    fun apprendre(): Pair<Int, Int> {
        if (session == null) { charger(); return exemples.size to etiquettes.toSet().size }
        val noms = especes.map { it.nom }.toMutableList()
        val textes = especes.map { vecteurTexte(it.sci) }.toMutableList()
        val sans = mutableListOf<Int>()
        val index = noms.withIndex().associate { cleEspece(it.value) to it.index }.toMutableMap()
        val vecteurs = mutableListOf<FloatArray>()
        val etiq = mutableListOf<Int>()
        val d = dossierCorrections
        if (d != null && d.isDirectory) {
            for (sous in d.listFiles { f -> f.isDirectory }!!.sortedBy { it.name }) {
                val photos = sous.listFiles { f -> f.name.endsWith(".jpg") }!!.sortedBy { it.name }
                if (photos.isEmpty()) continue
                val fichierNom = File(sous, "nom.txt")
                val nom = if (fichierNom.exists()) fichierNom.readText().trim() else sous.name.replace("_", " ")
                val cle = cleEspece(nom)
                if (cle !in index) {
                    index[cle] = noms.size
                    noms.add(nom)
                    val v = texteEspece(nom)
                    if (v == null) sans.add(index[cle]!!)
                    textes.add(v ?: FloatArray(512))
                }
                for (p in photos) {
                    vecteurPhoto(p)?.let { vecteurs.add(it); etiq.add(index[cle]!!) }
                }
            }
        }
        this.noms = noms
        // a priori : une espèce souvent observée ici est plus probable qu'une rareté
        // (log du nombre d'observations ; les espèces de vos corrections comptent comme courantes)
        val obs = especes.map { it.obs }
        val courant = obs.maxOrNull() ?: 0
        aPriori = FloatArray(noms.size) { i -> POIDS_A_PRIORI * ln(1.0 + (obs.getOrNull(i) ?: courant)).toFloat() }
        textesClasses = textes.toTypedArray()
        sansTexte = sans.toIntArray()
        exemples = vecteurs.toTypedArray()
        etiquettes = etiq.toIntArray()
        return exemples.size to etiq.toSet().size
    }

    /** Probabilité que la zone montre un oiseau (BioCLIP, zero-shot). */
    @Synchronized
    fun probOiseau(t: Trame, zone: Boite): Float {
        charger()
        val f = vecteurImage(t, zone)
        val logits = FloatArray(textesOiseau.size) { 100f * produit(textesOiseau[it], f) }
        val p = softmax(logits)
        return (0 until NB_OISEAU).sumOf { p[it].toDouble() }.toFloat()
    }

    /** Les top_k espèces les plus probables : [(espèce, probabilité)]. */
    @Synchronized
    fun classer(t: Trame, zone: Boite, topK: Int = 3): List<Pair<String, Float>> {
        charger()
        val f = vecteurImage(t, zone)
        val logits = FloatArray(noms.size) { 100f * produit(textesClasses[it], f) + aPriori[it] }
        if (sansTexte.isNotEmpty()) {
            // classes connues seulement par leurs exemples (« Pas un oiseau »...) : un cran sous la
            // meilleure espèce, elles l'emportent si l'image ressemble vraiment à un exemple
            val max = logits.max()
            for (c in sansTexte) logits[c] = max - MARGE
        }
        if (exemples.isNotEmpty()) {
            val affinite = FloatArray(exemples.size) { exp(-BETA * (1f - produit(exemples[it], f))) }
            for (c in etiquettes.distinct()) {
                val proches = etiquettes.indices.filter { etiquettes[it] == c }.map { affinite[it] }.sortedDescending().take(3)
                logits[c] += ALPHA * proches.average().toFloat()
            }
        }
        val p = softmax(logits)
        return p.indices.sortedByDescending { p[it] }.take(topK).map { noms[it] to p[it] }
    }

    private fun produit(a: FloatArray, b: FloatArray): Float {
        var s = 0f
        for (i in a.indices) s += a[i] * b[i]
        return s
    }

    private fun softmax(x: FloatArray): FloatArray {
        val m = x.max()
        val e = FloatArray(x.size) { exp(x[it] - m) }
        val s = e.sum()
        return FloatArray(x.size) { e[it] / s }
    }
}
