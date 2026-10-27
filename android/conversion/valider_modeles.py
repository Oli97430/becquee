"""
Vérifie les modèles convertis pour Android avant de construire l'APK : le moteur Windows tourne sur la
vidéo de test de La Réunion, mais avec les fichiers de assets/modeles/ (ONNX int8, vecteurs texte
précalculés) et le prétraitement du téléphone (redimensionnement bilinéaire). Mêmes critères que
logiciel/tests/test_moteur.py : 12 espèces justes, faux visiteur effacé.

    ..\..\logiciel\venv\Scripts\python valider_modeles.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

ICI = Path(__file__).resolve().parent
LOGICIEL = ICI.parent.parent / "logiciel"
MODELES = ICI.parent / "app" / "src" / "main" / "assets" / "modeles"
sys.path.insert(0, str(LOGICIEL))
import langues  # noqa: E402
from mangeoire_cam import DetecteurOiseaux, Reconnaisseur, Surveillance, especes_locales, lire_journal  # noqa: E402

MOYENNE_CLIP, ECART_CLIP = np.array([0.48145466, 0.4578275, 0.40821073]), np.array([0.26862954, 0.26130258, 0.27577711])
MOYENNE_IMAGENET, ECART_IMAGENET = np.array([0.485, 0.456, 0.406]), np.array([0.229, 0.224, 0.225])


def tenseur(image_bgr, largeur, hauteur, moyenne, ecart):
    rgb = cv2.cvtColor(cv2.resize(image_bgr, (largeur, hauteur), interpolation=cv2.INTER_LINEAR), cv2.COLOR_BGR2RGB)
    return ((rgb / 255.0 - moyenne) / ecart).transpose(2, 0, 1)[None].astype(np.float32)


def lire_f16(nom):
    return np.fromfile(MODELES / nom, np.float16).astype(np.float32).reshape(-1, 512)


class ReconnaisseurMobile(Reconnaisseur):
    def charger(self):
        with self._verrou:
            if self.modele is not None:
                return
            self.modele = ort.InferenceSession(str(MODELES / "bioclip_image.onnx"), providers=["CPUExecutionProvider"])
            noms = [l for l in (MODELES / "bioclip_textes.txt").read_text(encoding="utf-8").splitlines() if l]
            self.table = dict(zip(noms, lire_f16("bioclip_textes.bin")))
            self._textes_oiseau = lire_f16("bioclip_oiseau.bin")
            self.especes = especes_locales(self.dossier_modeles, self.latitude, self.longitude, self.sur_message)
            manquantes = [e["sci"] for e in self.especes if e["sci"] not in self.table]
            if manquantes:
                print("  absentes de la table :", manquantes)
            generique = lire_f16("bioclip_oiseau_generique.bin")[0]
            self.textes = np.stack([self.table.get(e["sci"], generique) for e in self.especes])
            self.apprendre()

    def _vecteur_image(self, image_pil):
        bgr = cv2.cvtColor(np.asarray(image_pil.convert("RGB")), cv2.COLOR_RGB2BGR)
        return self.modele.run(None, {"image": tenseur(bgr, 224, 224, MOYENNE_CLIP, ECART_CLIP)})[0][0]


class DetecteurMobile(DetecteurOiseaux):
    def charger(self):
        with self._verrou:
            if self.pipe is None:
                self.config = json.loads((MODELES / "yolos_tiny.json").read_text())
                self.pipe = ort.InferenceSession(str(MODELES / "yolos_tiny.onnx"), providers=["CPUExecutionProvider"])

    def detecter(self, image_bgr):
        self.charger()
        h, w = image_bgr.shape[:2]
        c = self.config
        logits, boites = self.pipe.run(None, {"image": tenseur(image_bgr, c["largeur"], c["hauteur"],
                                                               MOYENNE_IMAGENET, ECART_IMAGENET)})
        p = np.exp(logits[0] - logits[0].max(-1, keepdims=True))
        p = (p / p.sum(-1, keepdims=True))[:, :-1]
        oiseaux = []
        for q in np.where((p.argmax(-1) == c["classe_oiseau"]) & (p.max(-1) > self.seuil))[0]:
            cx, cy, bw, bh = boites[0, q]
            oiseaux.append((float(p[q].max()), (int((cx - bw / 2) * w), int((cy - bh / 2) * h), int(bw * w), int(bh * h))))
        return sorted(oiseaux, key=lambda o: o[1][2] * o[1][3], reverse=True)


ATTENDUES = {"Martin triste", "Astrild ondulé", "Foudi rouge", "Géopélie zébrée", "Bulbul de Bourbon",
             "Moineau domestique", "Tisserin gendarme", "Bulbul orphée", "Tarier de La Réunion",
             "Tchitrec des Mascareignes", "Zostérops des Mascareignes", "Zostérops de la Réunion"}

if __name__ == "__main__":
    langues.regler("fr")
    messages = []
    with tempfile.TemporaryDirectory() as dossier:
        debut = time.time()
        r = ReconnaisseurMobile(LOGICIEL / "modeles", -21.1, 55.5, sur_message=messages.append)
        Surveillance(LOGICIEL / "tests" / "videos" / "mangeoire_reunion.mp4", dossier, reconnaisseur=r,
                     detecteur_oiseaux=DetecteurMobile(), sur_message=messages.append).executer()
        visites = lire_journal(dossier)
    trouvees = [v["espece"] for v in visites]
    for v in visites:
        print(f"  {v['heure']}  {v['espece']:30s} {v['confiance']}")
    print(f"{len(set(trouvees) & ATTENDUES)}/{len(ATTENDUES)} espèces justes, {len(trouvees)} visites, "
          f"faux visiteur effacé : {any('sans oiseau' in m for m in messages)}, {time.time() - debut:.0f} s")
    ok = set(trouvees) == ATTENDUES and len(trouvees) == len(ATTENDUES) and any("sans oiseau" in m for m in messages)
    sys.exit(0 if ok else 1)
