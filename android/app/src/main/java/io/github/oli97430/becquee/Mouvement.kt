package io.github.oli97430.becquee

import kotlin.math.max
import kotlin.math.min

/**
 * Détection de mouvement : même traitement que la version Windows (OpenCV), réécrit sans OpenCV.
 * Image réduite à 480 pixels de large, flou gaussien 5x5, soustraction de fond par mélange de
 * gaussiennes (MOG2 : historique 300, seuil 32, sans ombres), ouverture 3x3, dilatation 7x7 x 2,
 * puis plus grande zone en mouvement.
 */
class DetecteurMouvement(var surfaceMin: Float, private val largeurAnalyse: Int = 480) {
    private var fond: Mog2? = null

    /** Boîte du plus grand objet en mouvement, en pixels de l'image d'origine (ou null). */
    fun analyser(t: Trame): Boite? {
        val echelle = largeurAnalyse.toFloat() / t.largeur
        val w = largeurAnalyse
        val h = (t.hauteur * echelle + 0.5f).toInt()
        val rgb = Images.redimensionnerRgb(t, 0, 0, t.largeur, t.hauteur, w, h)
        for (plan in rgb) flouGaussien5(plan, w, h)
        val f = fond ?: Mog2(w, h).also { fond = it }
        var masque = f.appliquer(rgb)
        masque = dilater(eroder(masque, w, h, 1), w, h, 1)          // ouverture 3x3
        masque = dilater(dilater(masque, w, h, 3), w, h, 3)        // dilatation 7x7, deux fois
        val zone = plusGrandeZone(masque, w, h) ?: return null
        if (zone.second < surfaceMin * w * h) return null
        val b = zone.first
        return Boite((b.x / echelle).toInt(), (b.y / echelle).toInt(), (b.l / echelle).toInt(), (b.h / echelle).toInt())
    }

    // noyau gaussien 5x5 d'OpenCV pour sigma automatique : [1 4 6 4 1] / 16, bords en miroir (101)
    private fun flouGaussien5(p: FloatArray, w: Int, h: Int) {
        val k = floatArrayOf(1 / 16f, 4 / 16f, 6 / 16f, 4 / 16f, 1 / 16f)
        val tmp = FloatArray(p.size)
        for (y in 0 until h) for (x in 0 until w) {
            var s = 0f
            for (d in -2..2) s += k[d + 2] * p[y * w + miroir(x + d, w)]
            tmp[y * w + x] = s
        }
        for (y in 0 until h) for (x in 0 until w) {
            var s = 0f
            for (d in -2..2) s += k[d + 2] * tmp[miroir(y + d, h) * w + x]
            p[y * w + x] = s
        }
    }

    private fun miroir(i: Int, n: Int) = if (i < 0) -i else if (i >= n) 2 * n - 2 - i else i

    // morphologie à noyau carré (rayon r), séparable ; hors de l'image : sans effet (comme OpenCV)
    private fun eroder(m: BooleanArray, w: Int, h: Int, r: Int) = morpho(m, w, h, r, false)
    private fun dilater(m: BooleanArray, w: Int, h: Int, r: Int) = morpho(m, w, h, r, true)

    private fun morpho(m: BooleanArray, w: Int, h: Int, r: Int, dilatation: Boolean): BooleanArray {
        val tmp = BooleanArray(m.size)
        for (y in 0 until h) for (x in 0 until w) {
            var v = !dilatation
            for (xx in max(0, x - r)..min(w - 1, x + r)) {
                if (m[y * w + xx] == dilatation) { v = dilatation; break }
            }
            tmp[y * w + x] = v
        }
        val sortie = BooleanArray(m.size)
        for (y in 0 until h) for (x in 0 until w) {
            var v = !dilatation
            for (yy in max(0, y - r)..min(h - 1, y + r)) {
                if (tmp[yy * w + x] == dilatation) { v = dilatation; break }
            }
            sortie[y * w + x] = v
        }
        return sortie
    }

    /** Plus grande composante connexe (8-voisinage) : (boîte englobante, nombre de pixels). */
    private fun plusGrandeZone(m: BooleanArray, w: Int, h: Int): Pair<Boite, Int>? {
        val vu = BooleanArray(m.size)
        val pile = IntArray(m.size)
        var meilleure: Pair<Boite, Int>? = null
        for (depart in m.indices) {
            if (!m[depart] || vu[depart]) continue
            var n = 0
            var haut = 0
            var x0 = w; var y0 = h; var x1 = 0; var y1 = 0
            pile[haut++] = depart
            vu[depart] = true
            while (haut > 0) {
                val k = pile[--haut]
                val x = k % w
                val y = k / w
                n++
                x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
                for (dy in -1..1) for (dx in -1..1) {
                    val nx = x + dx
                    val ny = y + dy
                    if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue
                    val v = ny * w + nx
                    if (m[v] && !vu[v]) { vu[v] = true; pile[haut++] = v }
                }
            }
            if (meilleure == null || n > meilleure.second) meilleure = Boite(x0, y0, x1 - x0 + 1, y1 - y0 + 1) to n
        }
        return meilleure
    }
}

/** Portage du BackgroundSubtractorMOG2 d'OpenCV (image couleur, sans détection des ombres). */
private class Mog2(w: Int, h: Int) {
    private val modes = 5
    private val historique = 300
    private val seuil = 32f            // varThreshold (Tb)
    private val seuilGen = 9f          // varThresholdGen (Tg)
    private val rapportFond = 0.9f     // backgroundRatio
    private val varInit = 15f
    private val varMin = 4f
    private val varMax = 75f
    private val ct = 0.05f
    private val n = w * h
    private val poids = FloatArray(n * modes)
    private val variance = FloatArray(n * modes)
    private val moyenne = FloatArray(n * modes * 3)
    private val utilises = IntArray(n)
    private var nbImages = 0

    fun appliquer(rgb: Array<FloatArray>): BooleanArray {
        nbImages++
        val alphaT = 1f / min(2 * nbImages, historique)
        val alpha1 = 1f - alphaT
        val elagage = -alphaT * ct
        val masque = BooleanArray(n)
        val d = FloatArray(3)
        for (p in 0 until n) {
            // OpenCV travaille sur des octets 0..255 (image floutée arrondie)
            val x0 = Math.round(rgb[0][p] * 255f).toFloat()
            val x1 = Math.round(rgb[1][p] * 255f).toFloat()
            val x2 = Math.round(rgb[2][p] * 255f).toFloat()
            val g = p * modes
            var fond = false
            var correspond = false
            var total = 0f
            var nm = utilises[p]
            var mode = 0
            while (mode < nm) {
                var w = alpha1 * poids[g + mode] + elagage
                var echanges = 0
                if (!correspond) {
                    val v = variance[g + mode]
                    val m = (g + mode) * 3
                    d[0] = moyenne[m] - x0; d[1] = moyenne[m + 1] - x1; d[2] = moyenne[m + 2] - x2
                    val dist2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2]
                    if (total < rapportFond && dist2 < seuil * v) fond = true
                    if (dist2 < seuilGen * v) {
                        correspond = true
                        w += alphaT
                        val k = alphaT / w
                        for (c in 0 until 3) moyenne[m + c] -= k * d[c]
                        variance[g + mode] = min(max(v + k * (dist2 - v), varMin), varMax)
                        var i = mode
                        while (i > 0) {
                            if (w < poids[g + i - 1]) break
                            echanges++
                            echanger(g, i, i - 1)
                            i--
                        }
                    }
                }
                if (w < -elagage) { w = 0f; nm-- }
                poids[g + mode - echanges] = w
                total += w
                mode++
            }
            if (total > 0f) {
                val inv = 1f / total
                for (k in 0 until nm) poids[g + k] *= inv
            }
            if (!correspond) {
                val nouveau = if (nm == modes) modes - 1 else nm++
                if (nm == 1) poids[g + nouveau] = 1f
                else {
                    poids[g + nouveau] = alphaT
                    for (k in 0 until nm - 1) poids[g + k] *= alpha1
                }
                val m = (g + nouveau) * 3
                moyenne[m] = x0; moyenne[m + 1] = x1; moyenne[m + 2] = x2
                variance[g + nouveau] = varInit
                var i = nm - 1
                while (i > 0) {
                    if (alphaT < poids[g + i - 1]) break
                    echanger(g, i, i - 1)
                    i--
                }
            }
            utilises[p] = nm
            masque[p] = !fond
        }
        return masque
    }

    private fun echanger(g: Int, a: Int, b: Int) {
        var t = poids[g + a]; poids[g + a] = poids[g + b]; poids[g + b] = t
        t = variance[g + a]; variance[g + a] = variance[g + b]; variance[g + b] = t
        for (c in 0 until 3) {
            t = moyenne[(g + a) * 3 + c]; moyenne[(g + a) * 3 + c] = moyenne[(g + b) * 3 + c]; moyenne[(g + b) * 3 + c] = t
        }
    }
}
