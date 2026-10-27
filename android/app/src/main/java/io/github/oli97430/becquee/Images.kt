package io.github.oli97430.becquee

import android.graphics.Bitmap
import java.io.File
import kotlin.math.max
import kotlin.math.min

/** Image du flux : pixels ARGB (0xAARRGGBB) ligne par ligne, et son instant en microsecondes. */
class Trame(val pixels: IntArray, val largeur: Int, val hauteur: Int, val tempsUs: Long) {
    fun bitmap(): Bitmap = Bitmap.createBitmap(pixels, largeur, hauteur, Bitmap.Config.ARGB_8888)
}

/** Boîte en pixels de l'image d'origine (comme les boîtes (x, y, l, h) d'OpenCV). */
data class Boite(val x: Int, val y: Int, val l: Int, val h: Int)

object Images {
    /** Redimensionnement bilinéaire, mêmes conventions qu'OpenCV (INTER_LINEAR, centres des pixels) :
     *  c'est avec lui que les modèles convertis ont été validés sur le PC. Sortie en RGB float [0, 1]
     *  par canal (plans R, G, B), à partir d'une zone (x0, y0, l, h) de l'image. */
    fun redimensionnerRgb(t: Trame, x0: Int, y0: Int, l: Int, h: Int, largeur: Int, hauteur: Int): Array<FloatArray> {
        val r = FloatArray(largeur * hauteur)
        val g = FloatArray(largeur * hauteur)
        val b = FloatArray(largeur * hauteur)
        val ex = l.toFloat() / largeur
        val ey = h.toFloat() / hauteur
        for (j in 0 until hauteur) {
            val sy = (j + 0.5f) * ey - 0.5f
            val y1 = sy.toInt().let { if (sy < 0) -1 else it }
            val fy = sy - y1
            val ya = y0 + min(max(y1, 0), h - 1)
            val yb = y0 + min(max(y1 + 1, 0), h - 1)
            for (i in 0 until largeur) {
                val sx = (i + 0.5f) * ex - 0.5f
                val x1 = sx.toInt().let { if (sx < 0) -1 else it }
                val fx = sx - x1
                val xa = x0 + min(max(x1, 0), l - 1)
                val xb = x0 + min(max(x1 + 1, 0), l - 1)
                val p00 = t.pixels[ya * t.largeur + xa]
                val p01 = t.pixels[ya * t.largeur + xb]
                val p10 = t.pixels[yb * t.largeur + xa]
                val p11 = t.pixels[yb * t.largeur + xb]
                val k = j * largeur + i
                r[k] = melange(p00 shr 16, p01 shr 16, p10 shr 16, p11 shr 16, fx, fy)
                g[k] = melange(p00 shr 8, p01 shr 8, p10 shr 8, p11 shr 8, fx, fy)
                b[k] = melange(p00, p01, p10, p11, fx, fy)
            }
        }
        return arrayOf(r, g, b)
    }

    private fun melange(a: Int, b: Int, c: Int, d: Int, fx: Float, fy: Float): Float {
        val haut = (a and 0xFF) * (1 - fx) + (b and 0xFF) * fx
        val bas = (c and 0xFF) * (1 - fx) + (d and 0xFF) * fx
        return (haut * (1 - fy) + bas * fy) / 255f
    }

    /** Tenseur 1 x 3 x H x W normalisé (moyenne / écart-type par canal). */
    fun tenseur(rgb: Array<FloatArray>, moyenne: FloatArray, ecart: FloatArray): FloatArray {
        val n = rgb[0].size
        val sortie = FloatArray(3 * n)
        for (c in 0 until 3) {
            val plan = rgb[c]
            for (k in 0 until n) sortie[c * n + k] = (plan[k] - moyenne[c]) / ecart[c]
        }
        return sortie
    }

    /** Recadrage carré autour d'une boîte (le modèle attend un oiseau centré) : (x0, y0, côté). */
    fun recadrer(largeur: Int, hauteur: Int, b: Boite, marge: Float = 0.15f): Boite {
        val cote = min(min((max(b.l, b.h) * (1 + 2 * marge)).toInt(), largeur), hauteur)
        val cx = b.x + b.l / 2
        val cy = b.y + b.h / 2
        val x0 = max(0, min(largeur - cote, cx - cote / 2))
        val y0 = max(0, min(hauteur - cote, cy - cote / 2))
        return Boite(x0, y0, cote, cote)
    }

    fun extraire(t: Trame, b: Boite): Bitmap = Bitmap.createBitmap(t.pixels, b.y * t.largeur + b.x, t.largeur, b.l, b.h,
        Bitmap.Config.ARGB_8888)

    fun enregistrerJpeg(bitmap: Bitmap, fichier: File) {
        fichier.outputStream().use { bitmap.compress(Bitmap.CompressFormat.JPEG, 92, it) }
    }

    fun depuisBitmap(bitmap: Bitmap, tempsUs: Long): Trame {
        val b = if (bitmap.config == Bitmap.Config.ARGB_8888) bitmap else bitmap.copy(Bitmap.Config.ARGB_8888, false)
        val pixels = IntArray(b.width * b.height)
        b.getPixels(pixels, 0, b.width, 0, 0, b.width, b.height)
        return Trame(pixels, b.width, b.height, tempsUs)
    }

    /** Rotation par quart de tour (l'image de la caméra arrive dans le sens du capteur). */
    fun tourner(t: Trame, degres: Int): Trame {
        if (degres % 360 == 0) return t
        val w = t.largeur
        val h = t.hauteur
        val p = t.pixels
        return when ((degres % 360 + 360) % 360) {
            90 -> Trame(IntArray(w * h).also { s -> for (y in 0 until h) for (x in 0 until w) s[x * h + (h - 1 - y)] = p[y * w + x] }, h, w, t.tempsUs)
            180 -> Trame(IntArray(w * h).also { s -> for (k in 0 until w * h) s[w * h - 1 - k] = p[k] }, w, h, t.tempsUs)
            else -> Trame(IntArray(w * h).also { s -> for (y in 0 until h) for (x in 0 until w) s[(w - 1 - x) * h + y] = p[y * w + x] }, h, w, t.tempsUs)
        }
    }

    /** ARGB -> YUV 4:2:0 planaire (I420, BT.601 « vidéo ») pour l'encodeur H.264. */
    fun versI420(t: Trame): ByteArray {
        val w = t.largeur
        val h = t.hauteur
        val sortie = ByteArray(w * h * 3 / 2)
        val u0 = w * h
        val v0 = u0 + (w / 2) * (h / 2)
        for (y in 0 until h) {
            for (x in 0 until w) {
                val p = t.pixels[y * w + x]
                val r = (p shr 16) and 0xFF
                val g = (p shr 8) and 0xFF
                val b = p and 0xFF
                sortie[y * w + x] = (((66 * r + 129 * g + 25 * b + 128) shr 8) + 16).toByte()
                if (y % 2 == 0 && x % 2 == 0) {
                    val k = (y / 2) * (w / 2) + x / 2
                    sortie[u0 + k] = (((-38 * r - 74 * g + 112 * b + 128) shr 8) + 128).toByte()
                    sortie[v0 + k] = (((112 * r - 94 * g - 18 * b + 128) shr 8) + 128).toByte()
                }
            }
        }
        return sortie
    }
}
