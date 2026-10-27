package io.github.oli97430.becquee

import java.io.File

/**
 * Journal des visites (visites.csv) : même format que la version Windows (séparateur « ; »,
 * mêmes colonnes), pour pouvoir ouvrir le dossier d'un téléphone avec l'appli du PC.
 */
class Journal(private val dossier: File) {
    companion object {
        val COLONNES = listOf("date", "heure", "duree_s", "espece", "confiance", "video", "photo", "source", "chants", "corrige")
    }

    private val fichier = File(dossier, "visites.csv")

    @Synchronized
    fun lire(): List<MutableMap<String, String>> {
        if (!fichier.exists()) return emptyList()
        val lignes = fichier.readLines(Charsets.UTF_8).filter { it.isNotBlank() }
        if (lignes.isEmpty()) return emptyList()
        val entete = decouper(lignes[0])
        return lignes.drop(1).map { l -> entete.zip(decouper(l)).toMap().toMutableMap() }
    }

    @Synchronized
    fun ajouter(ligne: Map<String, String>) {
        dossier.mkdirs()
        if (!fichier.exists()) fichier.writeText(COLONNES.joinToString(";") + "\r\n", Charsets.UTF_8)
        fichier.appendText(COLONNES.joinToString(";") { champ(ligne[it] ?: "") } + "\r\n", Charsets.UTF_8)
    }

    @Synchronized
    fun ecrire(lignes: List<Map<String, String>>) {
        val tmp = File(dossier, "visites.tmp")
        tmp.writeText((listOf(COLONNES.joinToString(";")) + lignes.map { l -> COLONNES.joinToString(";") { champ(l[it] ?: "") } })
            .joinToString("\r\n", postfix = "\r\n"), Charsets.UTF_8)
        tmp.renameTo(fichier)
    }

    /**
     * Corrige l'espèce d'une visite ; copie l'oiseau recadré (à défaut la photo) dans
     * corrections/<espèce>/ : le reconnaisseur apprend de ces photos (Reconnaisseur.apprendre).
     */
    fun corriger(video: String, espece: String): Boolean {
        val lignes = lire()
        val ligne = lignes.firstOrNull { it["video"] == video } ?: return false
        ligne["espece"] = espece
        ligne["corrige"] = "1"
        ligne["source"] = "manuel"
        ecrire(lignes)
        // le journal peut avoir été modifié à la main : nom de fichier simple, dans le dossier des visites
        val photo = File(ligne["photo"].orEmpty()).name
        if (photo.isNotEmpty() && photo != "..") {
            val p = File(dossier, photo)
            val recadrage = File(dossier, p.nameWithoutExtension + "_oiseau.jpg")
            val source = if (recadrage.exists()) recadrage else p
            if (source.exists()) {
                // une visite corrigée deux fois ne doit rester que dans la dernière espèce
                File(dossier, "corrections").listFiles()?.forEach { File(it, p.name).delete() }
                val cible = File(File(dossier, "corrections"), nomFichier(espece)).apply { mkdirs() }
                File(cible, "nom.txt").writeText(espece)
                source.copyTo(File(cible, p.name), overwrite = true)
            }
        }
        return true
    }

    private fun champ(v: String) = if (v.contains(';') || v.contains('"') || v.contains('\n')) "\"" + v.replace("\"", "\"\"") + "\"" else v

    private fun decouper(l: String): List<String> {
        val champs = mutableListOf<String>()
        val b = StringBuilder()
        var guillemets = false
        var i = 0
        while (i < l.length) {
            val c = l[i]
            when {
                guillemets && c == '"' && i + 1 < l.length && l[i + 1] == '"' -> { b.append('"'); i++ }
                c == '"' -> guillemets = !guillemets
                c == ';' && !guillemets -> { champs.add(b.toString()); b.clear() }
                else -> b.append(c)
            }
            i++
        }
        champs.add(b.toString())
        return champs
    }
}
