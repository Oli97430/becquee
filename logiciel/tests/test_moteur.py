"""Vérifie le moteur de bout en bout sur les vidéos de test de La Réunion : espèces justes,
aucune « Inconnu », et le faux visiteur (mouvement sans oiseau) effacé.
python tests/test_moteur.py           (code de sortie 1 en cas d'échec ; ~1 min sur GPU, ~2 min sur CPU)"""
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import langues
from mangeoire_cam import DetecteurOiseaux, Reconnaisseur, Surveillance, appareil, lire_journal

COMMUNES = {"Martin triste", "Géopélie zébrée", "Bulbul de Bourbon", "Moineau domestique", "Tisserin gendarme",
            "Bulbul orphée", "Tarier de La Réunion", "Tchitrec des Mascareignes", "Zostérops des Mascareignes",
            "Zostérops de la Réunion"}
VIDEOS = {
    "mangeoire_reunion.mp4": COMMUNES | {"Astrild ondulé", "Foudi rouge"},
    # autres photos, dont un Bulbul de Bourbon à contre-jour (pris pour une Perruche à collier sans egaliser())
    "mangeoire_reunion2.mp4": COMMUNES,
}

langues.regler("fr")
reconnaisseur = Reconnaisseur(ICI / "modeles", -21.1, 55.5, sur_message=lambda m: None)
detecteur = DetecteurOiseaux()
problemes = []
for video, attendues in VIDEOS.items():
    messages = []
    with tempfile.TemporaryDirectory() as dossier:
        debut = time.time()
        s = Surveillance(ICI / "tests" / "videos" / video, dossier, reconnaisseur=reconnaisseur,
                         detecteur_oiseaux=detecteur, sur_message=messages.append)
        s.executer()
        visites = lire_journal(dossier)
        clips = list(Path(dossier).glob("*.mp4"))
        galerie = list(Path(dossier, "galerie").glob("*.jpg"))
        duree = time.time() - debut

    trouvees = [v["espece"] for v in visites]
    erreurs = [f"espèce manquée : {e}" for e in sorted(attendues - set(trouvees))]
    erreurs += [f"espèce en trop : {e}" for e in sorted(set(trouvees) - attendues)]
    if len(trouvees) != len(attendues):
        erreurs.append(f"{len(trouvees)} visites au lieu de {len(attendues)}")
    if not any("sans oiseau" in m for m in messages):
        erreurs.append("le faux visiteur n'a pas été effacé")
    if len(clips) != len(visites):
        erreurs.append(f"{len(clips)} clips pour {len(visites)} visites")
    if len(galerie) != len(attendues):
        erreurs.append(f"galerie : {len(galerie)} photos au lieu de {len(attendues)}")
    print(f"{video} : {len(set(trouvees) & attendues)}/{len(attendues)} espèces justes en {duree:.0f} s ({appareil()})")
    for e in erreurs:
        print("  PROBLÈME :", e)
    problemes += erreurs
sys.exit(1 if problemes else 0)
