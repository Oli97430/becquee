package io.github.oli97430.becquee

import ai.onnxruntime.OrtSession
import android.content.Context
import org.json.JSONObject
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.min

/** Trouve les oiseaux dans l'image (YOLOS-tiny, détecteur d'objets COCO, classe « bird »). */
class DetecteurOiseaux(private val context: Context, private val seuil: Float = 0.5f) {
    private var session: OrtSession? = null
    private var classeOiseau = 16
    private var hauteur = 512
    private var largeur = 672
    private val moyenne = floatArrayOf(0.485f, 0.456f, 0.406f)
    private val ecart = floatArrayOf(0.229f, 0.224f, 0.225f)

    @Synchronized
    fun charger() {
        if (session != null) return
        val c = JSONObject(Modeles.texte(context, "yolos_tiny.json"))
        classeOiseau = c.getInt("classe_oiseau")
        hauteur = c.getInt("hauteur")
        largeur = c.getInt("largeur")
        session = Modeles.session(context, "yolos_tiny.onnx")
    }

    /** Liste de (score, boîte) en pixels de l'image d'origine, du plus grand au plus petit. */
    @Synchronized
    fun detecter(t: Trame): List<Pair<Float, Boite>> {
        charger()
        // le modèle a une entrée fixe 4:3 : une image 4:3 est étirée comme le fait le processeur YOLOS ;
        // une image d'un autre format est centrée sur un fond neutre
        var ex = largeur.toFloat() / t.largeur
        var ey = hauteur.toFloat() / t.hauteur
        if (abs(ex / ey - 1f) > 0.05f) { ex = min(ex, ey); ey = ex }
        val lu = min(Math.round(t.largeur * ex), largeur)
        val hu = min(Math.round(t.hauteur * ey), hauteur)
        val rgb = Images.redimensionnerRgb(t, 0, 0, t.largeur, t.hauteur, lu, hu)
        val entree = FloatArray(3 * largeur * hauteur)       // 0 = couleur moyenne après normalisation
        val dx = (largeur - lu) / 2
        val dy = (hauteur - hu) / 2
        for (c in 0 until 3) for (y in 0 until hu) for (x in 0 until lu)
            entree[c * largeur * hauteur + (y + dy) * largeur + x + dx] = (rgb[c][y * lu + x] - moyenne[c]) / ecart[c]
        val (logits, boites) = Modeles.executer(session!!, entree, longArrayOf(1, 3, hauteur.toLong(), largeur.toLong()))
        val nbClasses = logits.size / (boites.size / 4)
        val oiseaux = mutableListOf<Pair<Float, Boite>>()
        for (q in 0 until boites.size / 4) {
            // softmax sur les classes, sans la dernière (« pas d'objet »)
            val o = q * nbClasses
            var m = Float.NEGATIVE_INFINITY
            for (k in 0 until nbClasses) m = maxOf(m, logits[o + k])
            var s = 0f
            for (k in 0 until nbClasses) s += exp(logits[o + k] - m)
            var meilleure = 0
            for (k in 1 until nbClasses - 1) if (logits[o + k] > logits[o + meilleure]) meilleure = k
            val score = exp(logits[o + meilleure] - m) / s
            if (meilleure != classeOiseau || score <= seuil) continue
            // boîte (cx, cy, l, h) relative à l'entrée du modèle -> pixels de l'image d'origine
            val cx = boites[q * 4] * largeur - dx
            val cy = boites[q * 4 + 1] * hauteur - dy
            val bl = boites[q * 4 + 2] * largeur
            val bh = boites[q * 4 + 3] * hauteur
            oiseaux.add(score to Boite(((cx - bl / 2) / ex).toInt(), ((cy - bh / 2) / ey).toInt(), (bl / ex).toInt(), (bh / ey).toInt()))
        }
        return oiseaux.sortedByDescending { it.second.l * it.second.h }
    }
}
