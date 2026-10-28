"""
Becquée Android — conversion des modèles pour le téléphone (à lancer une fois sur le PC).

    ..\..\logiciel\venv\Scripts\python convertir_modeles.py

Produit dans android/app/src/main/assets/modeles/ :
  - bioclip_image.onnx      encodeur d'image de BioCLIP, poids int8 (l'encodeur de texte reste sur le PC)
  - bioclip_textes.bin      vecteurs texte précalculés de toutes les espèces d'oiseaux (float16, N x 512)
  - bioclip_textes.txt      une ligne par vecteur : nom scientifique
  - bioclip_oiseau.bin      vecteurs des phrases « oiseau / pas oiseau » (Reconnaisseur.OISEAU + AUTRES)
  - yolos_tiny.onnx         détecteur d'objets COCO (classe « bird »), entrée fixe 384 x 512, poids int8
  - birdnet_data_model.onnx méta-modèle géographique de BirdNET (liste d'espèces hors ligne)
  - BirdNET_GLOBAL_6K_V2.4_Labels*.txt  noms d'espèces traduits

Prérequis : l'environnement de logiciel/ (torch, open_clip, transformers, onnx, onnxruntime) + onnx_ir
(pip install onnx_ir)
et les modèles déjà téléchargés par l'application Windows (logiciel/modeles/).
"""
import json
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import torch

ICI = Path(__file__).resolve().parent
LOGICIEL = ICI.parent.parent / "logiciel"
SORTIE = ICI.parent / "app" / "src" / "main" / "assets" / "modeles"
CACHE = ICI / "cache"
sys.path.insert(0, str(LOGICIEL))
from mangeoire_cam import MODELE_BIOCLIP, MODELE_DETECTION, NON_OISEAUX, Reconnaisseur  # noqa: E402

AGENT = {"User-Agent": "Becquee/1.0 (conversion Android)"}
# hauteur, largeur. Le processeur YOLOS donnerait 512 x 672 pour une image 4:3 ; en 384 x 512 le détecteur
# est 2,1 fois plus rapide sur le téléphone, avec les mêmes visites sur les deux vidéos de test
TAILLE_YOLOS = (384, 512)


def quantifier(entree, sortie):
    """Poids des produits matriciels en int8 par blocs de 128, calculs en float32 (MatMulNBits) :
    la quantification dynamique classique (activations int8 aussi) dégrade trop BioCLIP
    (similarité 0,95 avec le modèle d'origine, contre 0,9997 ici) et fait rater un oiseau du test."""
    import onnx
    from onnxruntime.quantization.matmul_nbits_quantizer import DefaultWeightOnlyQuantConfig, MatMulNBitsQuantizer
    modele = onnx.load(str(entree))
    gemm_en_matmul(modele)
    q = MatMulNBitsQuantizer(modele,
                             algo_config=DefaultWeightOnlyQuantConfig(block_size=128, is_symmetric=True, bits=8))
    q.process()
    q.model.save_model_to_file(str(sortie), False)
    entree.unlink()


def gemm_en_matmul(modele):
    """Gemm(A, B, C) à poids constants -> MatMul(A, Bᵀ) + C : seuls les MatMul sont quantifiés
    (les projections de sortie de l'attention de BioCLIP sont exportées en Gemm, 28 Mo en float32)."""
    from onnx import helper, numpy_helper
    poids = {t.name: t for t in modele.graph.initializer}
    nouveaux = []
    for n in modele.graph.node:
        attributs = {a.name: helper.get_attribute_value(a) for a in n.attribute}
        if (n.op_type != "Gemm" or n.input[1] not in poids or attributs.get("transA", 0)
                or attributs.get("alpha", 1.0) != 1.0 or attributs.get("beta", 1.0) != 1.0):
            nouveaux.append(n)
            continue
        b = numpy_helper.to_array(poids[n.input[1]])
        if attributs.get("transB", 0):
            b = b.T
        nom_b = n.input[1] + "_t"
        modele.graph.initializer.append(numpy_helper.from_array(np.ascontiguousarray(b), nom_b))
        if len(n.input) > 2 and n.input[2]:
            intermediaire = n.output[0] + "_matmul"
            nouveaux.append(helper.make_node("MatMul", [n.input[0], nom_b], [intermediaire], name=n.name + "_matmul"))
            nouveaux.append(helper.make_node("Add", [intermediaire, n.input[2]], list(n.output), name=n.name + "_add"))
        else:
            nouveaux.append(helper.make_node("MatMul", [n.input[0], nom_b], list(n.output), name=n.name + "_matmul"))
    del modele.graph.node[:]
    modele.graph.node.extend(nouveaux)
    utilises = {i for n in modele.graph.node for i in n.input}
    gardes = [t for t in modele.graph.initializer if t.name in utilises]
    del modele.graph.initializer[:]
    modele.graph.initializer.extend(gardes)


# ------------------------------------------------------------------
#  BioCLIP
# ------------------------------------------------------------------
class EncodeurImage(torch.nn.Module):
    """Image normalisée 1 x 3 x 224 x 224 -> vecteur unitaire 1 x 512."""

    def __init__(self, modele):
        super().__init__()
        self.visuel = modele.visual

    def forward(self, x):
        v = self.visuel(x)
        return v / v.norm(dim=-1, keepdim=True)


def exporter_bioclip(modele):
    brut = SORTIE / "bioclip_image_fp32.onnx"
    torch.onnx.export(EncodeurImage(modele).eval(), torch.randn(1, 3, 224, 224), str(brut),
                      input_names=["image"], output_names=["vecteur"], opset_version=17, dynamo=False)
    quantifier(brut, SORTIE / "bioclip_image.onnx")


def inaturalist_oiseaux():
    """Toutes les espèces d'oiseaux actives d'iNaturalist : {sci: nom anglais} (mis en cache)."""
    fichier = CACHE / "inaturalist_aves.json"
    if fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8"))
    especes, dernier = {}, 0
    while True:
        q = urllib.parse.urlencode({"taxon_id": 3, "rank": "species", "is_active": "true", "per_page": 500,
                                    "order_by": "id", "order": "asc", "id_above": dernier, "locale": "en"})
        for essai in range(5):          # l'API coupe parfois la connexion : on réessaie
            try:
                r = json.load(urllib.request.urlopen(urllib.request.Request(
                    "https://api.inaturalist.org/v1/taxa?" + q, headers=AGENT), timeout=60))["results"]
                break
            except OSError:
                if essai == 4:
                    raise
                time.sleep(10 * (essai + 1))
        if not r:
            break
        for t in r:
            especes[t["name"]] = t.get("preferred_common_name") or ""
        dernier = r[-1]["id"]
        print(f"  iNaturalist : {len(especes)} espèces")
        time.sleep(1)
    CACHE.mkdir(exist_ok=True)
    fichier.write_text(json.dumps(especes, ensure_ascii=False), encoding="utf-8")
    return especes


def table_textes(modele, tokenizer):
    # nom anglais : celui des listes locales déjà en cache sur le PC (texte identique à la version Windows),
    # puis iNaturalist, puis BirdNET
    especes = {}
    for ligne in (LOGICIEL / "modeles" / "BirdNET_GLOBAL_6K_V2.4_Labels.txt").read_text(encoding="utf-8").splitlines():
        sci, en = ligne.split("_", 1)
        if not any(m in sci.lower() for m in NON_OISEAUX):
            especes[sci] = en
    especes.update({sci: en for sci, en in inaturalist_oiseaux().items() if en or sci not in especes})
    for cache in (LOGICIEL / "modeles").glob("especes_*.json"):
        for e in json.loads(cache.read_text(encoding="utf-8")):
            especes[e["sci"]] = e.get("en") or ""
    noms = sorted(especes)
    print(f"Vecteurs texte : {len(noms)} espèces")

    def encoder(textes):
        with torch.no_grad():
            v = modele.encode_text(tokenizer(textes).cuda()).float()
        return (v / v.norm(dim=-1, keepdim=True)).cpu().numpy()

    vecteurs = np.concatenate([encoder([f"a photo of {s} ({especes[s]})." if especes[s] else f"a photo of {s}."
                                        for s in noms[i:i + 256]]) for i in range(0, len(noms), 256)])
    vecteurs.astype(np.float16).tofile(SORTIE / "bioclip_textes.bin")
    (SORTIE / "bioclip_textes.txt").write_text("\n".join(noms) + "\n", encoding="utf-8")
    encoder(Reconnaisseur.OISEAU + Reconnaisseur.AUTRES).astype(np.float16).tofile(SORTIE / "bioclip_oiseau.bin")
    # une espèce ajoutée par correction et absente de la table (nom libre) : « a photo of a bird, X. »
    # ne peut pas être calculé sur le téléphone ; on prend la phrase générique
    encoder(["a photo of a bird."]).astype(np.float16).tofile(SORTIE / "bioclip_oiseau_generique.bin")


# ------------------------------------------------------------------
#  YOLOS-tiny
# ------------------------------------------------------------------
class Detecteur(torch.nn.Module):
    def __init__(self, modele):
        super().__init__()
        self.modele = modele

    def forward(self, x):
        s = self.modele(pixel_values=x)
        return s.logits, s.pred_boxes


def exporter_yolos():
    from transformers import YolosForObjectDetection
    modele = YolosForObjectDetection.from_pretrained(MODELE_DETECTION).eval()
    oiseau = [i for i, n in modele.config.id2label.items() if n == "bird"][0]
    print(f"YOLOS : classe « bird » = {oiseau}")
    brut = SORTIE / "yolos_tiny_fp32.onnx"
    torch.onnx.export(Detecteur(modele), torch.randn(1, 3, *TAILLE_YOLOS), str(brut),
                      input_names=["image"], output_names=["logits", "boites"], opset_version=17, dynamo=False)
    quantifier(brut, SORTIE / "yolos_tiny.onnx")
    (SORTIE / "yolos_tiny.json").write_text(json.dumps({"classe_oiseau": int(oiseau), "hauteur": TAILLE_YOLOS[0],
                                                         "largeur": TAILLE_YOLOS[1]}), encoding="utf-8")


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    import open_clip
    modele, _entrainement, _pretraitement = open_clip.create_model_and_transforms(MODELE_BIOCLIP)
    modele.eval()
    print("Export de l'encodeur d'image de BioCLIP...")
    exporter_bioclip(modele)
    modele.cuda()
    table_textes(modele, open_clip.get_tokenizer(MODELE_BIOCLIP))
    print("Export de YOLOS-tiny...")
    exporter_yolos()
    for f in ["birdnet_data_model.onnx", *(p.name for p in (LOGICIEL / "modeles").glob("BirdNET_GLOBAL_6K_V2.4_Labels*.txt"))]:
        shutil.copy2(LOGICIEL / "modeles" / f, SORTIE / f)
    for f in sorted(SORTIE.iterdir()):
        print(f"  {f.name:42s} {f.stat().st_size / 1e6:7.1f} Mo")


if __name__ == "__main__":
    main()
