package io.github.oli97430.becquee

import android.content.Context

/** Réglages de l'appli (position de la mangeoire, seuils), gardés dans les préférences. */
class Reglages(context: Context) {
    private val p = context.getSharedPreferences("reglages", Context.MODE_PRIVATE)

    var latitude: Double?
        get() = p.getString("latitude", null)?.toDoubleOrNull()
        set(v) = p.edit().putString("latitude", v?.toString()).apply()
    var longitude: Double?
        get() = p.getString("longitude", null)?.toDoubleOrNull()
        set(v) = p.edit().putString("longitude", v?.toString()).apply()
    var seuil: Float
        get() = p.getFloat("seuil", 0.75f)
        set(v) = p.edit().putFloat("seuil", v).apply()
    var surface: Float
        get() = p.getFloat("surface", 0.01f)
        set(v) = p.edit().putFloat("surface", v).apply()
    var filtreOiseaux: Boolean
        get() = p.getBoolean("filtre_oiseaux", true)
        set(v) = p.edit().putBoolean("filtre_oiseaux", v).apply()

    var acceleration: String
        get() = p.getString("acceleration", "cpu") ?: "cpu"
        set(v) = p.edit().putString("acceleration", v).apply()
    var fils: Int
        get() = p.getInt("fils", 4)
        set(v) = p.edit().putInt("fils", v).apply()
    var son: Boolean
        get() = p.getBoolean("son", true)
        set(v) = p.edit().putBoolean("son", v).apply()
    var menageJours: Int
        get() = p.getInt("menage_jours", 60)
        set(v) = p.edit().putInt("menage_jours", v).apply()
    var menageGo: Float
        get() = p.getFloat("menage_go", 10f)
        set(v) = p.edit().putFloat("menage_go", v).apply()

    // le reconnaisseur (et sa liste d'espèces) est gardé tant que la position ne change pas
    private val position get() = "$latitude,$longitude,${Especes.langue()},$acceleration,$fils"
    fun retenir(r: Reconnaisseur) { cles[r] = position }
    fun memePosition(r: Reconnaisseur) = cles[r] == position

    companion object {
        private val cles = java.util.WeakHashMap<Reconnaisseur, String>()
    }
}
