"""Vérifie le moteur de bout en bout sur la vidéo de test de La Réunion : 12 espèces justes,
aucune « Inconnu », et le faux visiteur (mouvement sans oiseau) effacé.
python tests/test_moteur.py           (code de sortie 1 en cas d'échec ; ~30 s sur GPU, ~1 min sur CPU)"""
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import langues
from mangeoire_cam import DetecteurOiseaux, Reconnaisseur, Surveillance, appareil, lire_journal

ATTENDUES = {"Martin triste", "Astrild ondulé", "Foudi rouge", "Géopélie zébrée", "Bulbul de Bourbon",
             "Moineau domestique", "Tisserin gendarme", "Bulbul orphée", "Tarier de La Réunion",
             "Tchitrec des Mascareignes", "Zostérops des Mascareignes", "Zostérops de la Réunion"}

langues.regler("fr")
messages = []
with tempfile.TemporaryDirectory() as dossier:
    debut = time.time()
    reconnaisseur = Reconnaisseur(ICI / "modeles", -21.1, 55.5, sur_message=messages.append)
    s = Surveillance(ICI / "tests" / "videos" / "mangeoire_reunion.mp4", dossier, reconnaisseur=reconnaisseur,
                     detecteur_oiseaux=DetecteurOiseaux(), sur_message=messages.append)
    s.executer()
    visites = lire_journal(dossier)
    clips = list(Path(dossier).glob("*.mp4"))
    galerie = list(Path(dossier, "galerie").glob("*.jpg"))
    duree = time.time() - debut

problemes = []
trouvees = [v["espece"] for v in visites]
for espece in sorted(ATTENDUES - set(trouvees)):
    problemes.append(f"espèce manquée : {espece}")
for espece in sorted(set(trouvees) - ATTENDUES):
    problemes.append(f"espèce en trop : {espece}")
if len(trouvees) != len(ATTENDUES):
    problemes.append(f"{len(trouvees)} visites au lieu de {len(ATTENDUES)}")
if not any("sans oiseau" in m for m in messages):
    problemes.append("le faux visiteur n'a pas été effacé")
if len(clips) != len(visites):
    problemes.append(f"{len(clips)} clips pour {len(visites)} visites")
if len(galerie) != len(ATTENDUES):
    problemes.append(f"galerie : {len(galerie)} photos au lieu de {len(ATTENDUES)}")

print(f"{len(set(trouvees) & ATTENDUES)}/{len(ATTENDUES)} espèces justes en {duree:.0f} s ({appareil()})")
for p in problemes:
    print("  PROBLÈME :", p)
sys.exit(1 if problemes else 0)
