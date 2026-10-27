"""
Becquée — moteur : détection de mouvement, filtre « oiseau », enregistrement,
reconnaissance des espèces (image + chant) et ménage automatique.

Utilisé par l'application graphique (mangeoire_app.py) et par la ligne de commande.

Source vidéo :
  - webcam USB            : --source 0
  - smartphone (Android, appli "IP Webcam") : --source http://IP:8080/video
  - flux RTSP             : --source rtsp://...
  - caméra sur Internet   : --source https://www.youtube.com/watch?v=...  (page lue par yt-dlp)
                            ou adresse directe d'un flux (.m3u8...)
  - fichier vidéo         : --source enregistrement.mp4  (analyse a posteriori)

Pour chaque visite :
  1. un mouvement déclenche l'enregistrement (avec quelques secondes avant),
  2. un détecteur d'objets vérifie qu'il s'agit bien d'un oiseau ; sinon le
     clip est effacé (vent, feuilles, chat, personne...),
  3. l'espèce est reconnue sur l'oiseau recadré, sur plusieurs images,
  4. les chants entendus pendant la visite (BirdNET) complètent l'identification,
  5. la meilleure photo est gardée et la visite notée dans visites.csv.

Modèles (fonctionnent partout dans le monde) :
  - espèces (image) : BioCLIP (imageomics/bioclip), reconnaissance « zero-shot » parmi les
                      espèces observées autour de la position réglée (liste iNaturalist),
                      complétée par vos corrections (photos de corrections/)
  - filtre oiseau   : hustvl/yolos-tiny (détection d'objets COCO, classe « bird »)
  - chants          : BirdNET v2.4 (ONNX, ~6 000 espèces) + filtre géographique
"""

import argparse
import csv
import ipaddress
import json
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np

import langues
from langues import _

MODELE_BIOCLIP = "hf-hub:imageomics/bioclip"
MODELE_DETECTION = "hustvl/yolos-tiny"
DEPOT_BIRDNET = "justinchuby/BirdNET-onnx"
COLONNES = ["date", "heure", "duree_s", "espece", "confiance", "video", "photo", "source", "chants", "corrige"]
COLONNES_CHANTS = ["date", "heure", "espece", "nom_scientifique", "confiance"]
PAS_UN_OISEAU = "Pas un oiseau"
AGENT = {"User-Agent": "Becquee/1.0 (mangeoire connectee)"}


def sans_accents(texte):
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()


def cle_espece(nom):
    """Clé de comparaison tolérante (accents, tirets, casse) : 'Rouge-gorge' == 'Rougegorge'."""
    return "".join(c for c in sans_accents(nom).lower() if c.isalnum())


def nom_fichier(texte):
    # ASCII seulement : OpenCV ne sait pas écrire de chemins accentués sous Windows
    return "".join(c if c.isalnum() else "_" for c in sans_accents(texte)).strip("_")


def source_depuis_texte(texte):
    texte = str(texte).strip()
    return int(texte) if texte.isdigit() else texte


def est_flux_web(source):
    """Flux venu d'Internet (page YouTube, flux HLS d'un nid...) : ni webcam, ni fichier,
    ni appareil du réseau local (smartphone « IP Webcam », caméra RTSP de la maison)."""
    if not isinstance(source, str) or "://" not in source:
        return False
    hote = urllib.parse.urlparse(source).hostname or ""
    try:
        return not ipaddress.ip_address(hote).is_private
    except ValueError:
        return hote != "localhost" and not hote.endswith(".local")


def resoudre_flux(source):
    """Page web d'une caméra en direct (YouTube, Twitch...) -> adresse du flux vidéo, avec yt-dlp.
    À refaire à chaque connexion : les adresses YouTube expirent au bout de quelques heures.
    Un flux direct (.m3u8, .mp4, rtsp...) ou une page inconnue de yt-dlp est rendu tel quel."""
    if not est_flux_web(source) or not source.startswith("http"):
        return source
    if Path(urllib.parse.urlparse(source).path).suffix.lower() in (".m3u8", ".mpd", ".mp4", ".ts", ".flv",
                                                                  ".mjpg", ".mjpeg", ".jpg"):
        return source
    try:
        import yt_dlp
        options = {"quiet": True, "no_warnings": True, "noplaylist": True,
                   "format": "bestvideo[height<=720]/best[height<=720]/best"}   # le son n'est pas utilisé
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(source, download=False)["url"]
    except Exception:
        return source


def ouvrir_source(source):
    """Ouvre la caméra et lit une première image : (capture, image) ou (None, None).
    Webcam : Media Foundation d'abord, puis DirectShow (certaines webcams s'ouvrent
    sous Media Foundation mais ne renvoient plus d'images)."""
    if isinstance(source, str):
        source = resoudre_flux(source)
    essais = [(source, cv2.CAP_MSMF), (source, cv2.CAP_DSHOW)] if isinstance(source, int) else [(source, cv2.CAP_ANY)]
    for src, api in essais:
        camera = cv2.VideoCapture(src, api)
        if camera.isOpened():
            for _ in range(5):          # certaines webcams renvoient quelques images vides au démarrage
                ok, image = camera.read()
                if ok:
                    return camera, image
        camera.release()
    return None, None


# ------------------------------------------------------------------
#  Journal (visites.csv) et ménage
# ------------------------------------------------------------------
def assurer_journal(chemin, colonnes):
    """Crée le journal, ou ajoute les nouvelles colonnes à un ancien journal."""
    if not chemin.exists():
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerow(colonnes)
        return
    with open(chemin, encoding="utf-8") as f:
        entete = f.readline().strip().split(";")
    if entete != colonnes:
        with open(chemin, encoding="utf-8") as f:
            lignes = list(csv.DictReader(f, delimiter=";"))
        ecrire_journal(chemin, lignes, colonnes)


def ecrire_journal(chemin, lignes, colonnes=COLONNES):
    tmp = chemin.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for l in lignes:
            w.writerow({c: (l.get(c) or "") for c in colonnes})
    tmp.replace(chemin)


def ajouter_ligne(chemin, ligne, colonnes):
    with open(chemin, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=colonnes, delimiter=";", extrasaction="ignore").writerow(ligne)


def lire_journal(dossier, nom="visites.csv"):
    journal = Path(dossier) / nom
    if not journal.exists():
        return []
    with open(journal, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def corriger_visite(dossier, video, espece):
    """Corrige l'espèce d'une visite ; copie l'oiseau recadré (à défaut la photo) dans
    corrections/<espèce>/ : le reconnaisseur apprend de ces photos (Reconnaisseur.apprendre)."""
    dossier = Path(dossier)
    lignes = lire_journal(dossier)
    ligne = None
    for l in lignes:
        if l["video"] == video:
            l["espece"], l["corrige"], l["source"] = espece, "1", "manuel"
            ligne = l
    if ligne is None:
        return None
    ecrire_journal(dossier / "visites.csv", lignes)
    if ligne.get("photo"):
        photo = dossier / ligne["photo"]
        recadrage = photo.with_name(photo.stem + "_oiseau.jpg")
        source = recadrage if recadrage.exists() else photo
        if source.exists():
            # une visite corrigée deux fois ne doit rester que dans la dernière espèce
            for ancienne in (dossier / "corrections").glob(f"*/{photo.stem}.jpg"):
                ancienne.unlink()
            cible = dossier / "corrections" / nom_fichier(espece)
            cible.mkdir(parents=True, exist_ok=True)
            (cible / "nom.txt").write_text(espece, encoding="utf-8")
            (cible / photo.name).write_bytes(source.read_bytes())
    # la photo quitte la galerie de l'ancienne espèce ; vérifiée à la main, elle passe devant
    index = lire_galerie(dossier)
    for nom, e in list(index.items()):
        if e["video"] == video and nom != espece:
            (dossier / e["photo"]).unlink(missing_ok=True)
            del index[nom]
    _ecrire_galerie(dossier, index)
    garder_dans_galerie(dossier, {**ligne, "confiance": "1.00"})
    return ligne


# ------------------------------------------------------------------
#  Galerie : meilleure photo de chaque espèce (le ménage n'y touche pas)
# ------------------------------------------------------------------
def lire_galerie(dossier):
    try:
        return json.loads((Path(dossier) / "galerie" / "galerie.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _ecrire_galerie(dossier, index):
    chemin = Path(dossier) / "galerie" / "galerie.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")


def garder_dans_galerie(dossier, ligne):
    """Copie la photo de la visite dans galerie/ si c'est la plus sûre de son espèce."""
    dossier, espece = Path(dossier), ligne["espece"]
    if espece in ("Inconnu", PAS_UN_OISEAU) or not ligne.get("photo") or not (dossier / ligne["photo"]).exists():
        return False
    index = lire_galerie(dossier)
    ancienne = index.get(espece)
    if ancienne and float(ancienne["confiance"]) > float(ligne["confiance"]):
        return False
    photo = f"galerie/{nom_fichier(espece)}.jpg"
    source = dossier / ligne["photo"]
    recadrage = source.with_name(source.stem + "_oiseau.jpg")     # l'oiseau en gros plutôt que toute la scène
    (dossier / "galerie").mkdir(exist_ok=True)
    (dossier / photo).write_bytes((recadrage if recadrage.exists() else source).read_bytes())
    index[espece] = {"photo": photo, "confiance": ligne["confiance"], "date": ligne["date"],
                     "heure": ligne["heure"], "video": ligne["video"]}
    _ecrire_galerie(dossier, index)
    return True


def construire_galerie(dossier):
    """Première ouverture : la galerie est remplie avec les visites déjà notées."""
    for ligne in lire_journal(dossier):
        garder_dans_galerie(dossier, ligne)


def effacer_clips_interrompus(dossier):
    """Efface les clips jamais terminés (application coupée en pleine visite) : sans nom
    d'espèce, absents du journal et illisibles. Renvoie leur nombre."""
    dossier = Path(dossier)
    notes = {l["video"] for l in lire_journal(dossier)}
    n = 0
    for mp4 in dossier.glob("????-??-??_??-??-??.mp4"):
        if mp4.name in notes:
            continue
        lecture = cv2.VideoCapture(str(mp4))
        lisible = lecture.isOpened() and lecture.read()[0]
        lecture.release()
        if not lisible:
            try:
                mp4.unlink()
                n += 1
            except OSError:
                pass
    return n


def nettoyer(dossier, jours=60, max_go=20.0):
    """Efface les clips (mp4 + jpg) plus vieux que `jours`, puis les plus anciens
    tant que le dossier dépasse `max_go`. 0 = pas de limite. Le journal est conservé."""
    dossier = Path(dossier)
    clips = sorted(dossier.glob("*.mp4"), key=lambda p: p.name)
    supprimes = 0

    def effacer(mp4):
        nonlocal supprimes
        for p in (mp4, mp4.with_suffix(".jpg"), mp4.with_name(mp4.stem + "_oiseau.jpg")):
            try:
                p.unlink()
            except OSError:
                pass
        supprimes += 1

    if jours:
        limite = (datetime.now() - timedelta(days=jours)).strftime("%Y-%m-%d")
        for mp4 in [c for c in clips if c.name[:10] < limite]:
            effacer(mp4)
        clips = [c for c in clips if c.exists()]
    if max_go:
        taille = sum(p.stat().st_size for p in dossier.glob("*.*") if p.suffix in (".mp4", ".jpg"))
        while clips and taille > max_go * 1024**3:
            mp4 = clips.pop(0)
            taille -= mp4.stat().st_size + (mp4.with_suffix(".jpg").stat().st_size if mp4.with_suffix(".jpg").exists() else 0)
            effacer(mp4)
    return supprimes


# ------------------------------------------------------------------
#  Espèces locales (partout dans le monde)
# ------------------------------------------------------------------
NON_OISEAUX = ("human", "engine", "noise", "gun", "siren", "dog", "fireworks", "power tools")


def fichier_etiquettes(dossier_modeles, langue=None):
    """Étiquettes BirdNET dans la langue de l'interface (anglais d'origine si non traduites)."""
    suffixe = langues.ETIQUETTES_BIRDNET.get(langue or langues.langue)
    nom = f"BirdNET_GLOBAL_6K_V2.4_Labels_{suffixe}.txt" if suffixe else "BirdNET_GLOBAL_6K_V2.4_Labels.txt"
    return Path(dossier_modeles) / nom


def etiquettes_birdnet(dossier_modeles):
    """[(nom_scientifique, nom_anglais, nom_dans_la_langue)] des classes BirdNET (vide si absent)."""
    d = Path(dossier_modeles)
    en = d / "BirdNET_GLOBAL_6K_V2.4_Labels.txt"
    if not en.exists():
        return []
    lignes = en.read_text(encoding="utf-8").splitlines()
    local = fichier_etiquettes(d)
    noms = [l.split("_", 1)[-1] for l in local.read_text(encoding="utf-8").splitlines()] if local.exists() else []
    if len(noms) != len(lignes):
        noms = [l.split("_", 1)[-1] for l in lignes]
    return [(l.split("_", 1)[0], l.split("_", 1)[-1], n) for l, n in zip(lignes, noms)]


def probabilites_geo(dossier_modeles, latitude, longitude, semaines):
    """Méta-modèle BirdNET : probabilité de présence de chaque classe (max sur les semaines)."""
    import onnxruntime as ort
    s = ort.InferenceSession(str(Path(dossier_modeles) / "birdnet_data_model.onnx"), providers=["CPUExecutionProvider"])
    x = np.array([[latitude, longitude, w] for w in semaines], dtype=np.float32)
    return s.run(None, {s.get_inputs()[0].name: x})[0].max(axis=0)


def especes_birdnet(dossier_modeles, latitude=None, longitude=None):
    """Liste de secours : espèces BirdNET plausibles sur l'année à cette position (toutes sans position)."""
    etiquettes = etiquettes_birdnet(dossier_modeles)
    gardees = range(len(etiquettes))
    if latitude is not None and longitude is not None:
        try:
            p = probabilites_geo(dossier_modeles, latitude, longitude, range(1, 49))
            gardees = np.where(p >= 0.03)[0]
        except Exception:
            pass
    return [{"sci": etiquettes[i][0], "en": etiquettes[i][1], "nom": etiquettes[i][2], "obs": 0}
            for i in gardees if not any(m in etiquettes[i][0].lower() for m in NON_OISEAUX)]


def _inaturalist(latitude, longitude, rayon):
    q = urllib.parse.urlencode({"lat": latitude, "lng": longitude, "radius": rayon, "taxon_id": 3,
                                "quality_grade": "research", "rank": "species", "per_page": 500,
                                "locale": langues.LOCALE_INATURALIST.get(langues.langue, "en")})
    url = "https://api.inaturalist.org/v1/observations/species_counts?" + q
    resultats = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=30))["results"]
    especes = []
    for r in resultats:
        t = r["taxon"]
        nom = t.get("preferred_common_name") or t["name"]
        especes.append({"sci": t["name"], "nom": nom[:1].upper() + nom[1:],
                        "en": t.get("english_common_name") or "", "obs": r["count"]})
    return especes


def _completer_noms(especes, dossier_modeles):
    """iNaturalist n'a pas de nom commun dans toutes les langues pour toutes les espèces : à défaut,
    nom BirdNET traduit, puis nom anglais, plutôt que le nom scientifique."""
    if any(e["nom"] == e["sci"] for e in especes):
        birdnet = {sci: local for sci, en, local in etiquettes_birdnet(dossier_modeles) if local != en or
                   langues.langue == "en"}
        for e in especes:
            if e["nom"] == e["sci"]:
                e["nom"] = birdnet.get(e["sci"]) or e.get("en") or e["sci"]
    return especes


def especes_locales(dossier_modeles, latitude, longitude, sur_message=print):
    especes = _especes_locales(dossier_modeles, latitude, longitude, sur_message)
    return _completer_noms(especes, dossier_modeles) if latitude is not None and longitude is not None else especes


def _especes_locales(dossier_modeles, latitude, longitude, sur_message=print):
    """Espèces d'oiseaux observées autour de la position (iNaturalist, observations validées),
    des plus courantes aux plus rares : [{sci, nom (dans la langue de l'interface), en, obs}].
    Mise en cache 30 jours. Sans réseau : dernier cache, sinon le méta-modèle BirdNET ;
    sans position : toutes les espèces BirdNET."""
    if latitude is None or longitude is None:
        return especes_birdnet(dossier_modeles)
    cache = Path(dossier_modeles) / f"especes_{latitude:.2f}_{longitude:.2f}_{langues.langue}.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 30 * 86400:
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        for rayon in (50, 200, 1000):          # élargir dans les régions peu observées
            especes = _inaturalist(latitude, longitude, rayon)
            if len(especes) >= 40:
                break
        if not especes:
            raise ValueError("aucune observation")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(especes, ensure_ascii=False), encoding="utf-8")
        sur_message(_("Espèces locales : {n} (iNaturalist, rayon {rayon} km)", n=len(especes), rayon=rayon))
        return especes
    except Exception as e:
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))
        sur_message(_("Liste iNaturalist indisponible ({erreur}) : liste BirdNET", erreur=type(e).__name__))
        return especes_birdnet(dossier_modeles, latitude, longitude)


# pays essayé en premier pour un code postal seul (sinon 97400 donne la Crimée, 75001 le Texas…)
PAYS_CODE_POSTAL = {"fr": "fr", "es": "es", "de": "de", "pt": "br", "it": "it"}


def chercher_lieu(texte):
    """Ville ou adresse -> (latitude, longitude, nom complet), via OpenStreetMap (Nominatim)."""
    def nominatim(**params):
        q = urllib.parse.urlencode({**params, "format": "json", "limit": 1, "accept-language": langues.langue})
        return json.load(urllib.request.urlopen(urllib.request.Request(
            "https://nominatim.openstreetmap.org/search?" + q, headers=AGENT), timeout=20))

    r = []
    code = texte.replace(" ", "")
    pays = PAYS_CODE_POSTAL.get(langues.langue)
    if code.isdigit() and pays:
        r = nominatim(postalcode=code, countrycodes=pays)
    if not r:
        r = nominatim(q=texte)
    if not r:
        return None
    return round(float(r[0]["lat"]), 3), round(float(r[0]["lon"]), 3), r[0]["display_name"]


# ------------------------------------------------------------------
#  Modèles image
# ------------------------------------------------------------------
def appareil():
    """« cuda » si une carte graphique NVIDIA est utilisable (PyTorch CUDA installé), sinon « cpu »."""
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


class Reconnaisseur:
    """Espèce à partir d'une image d'oiseau recadrée, avec BioCLIP (modèle du vivant entraîné
    sur l'arbre de la vie : il reconnaît une espèce à partir de son nom scientifique).

    Candidats : les espèces locales (especes_locales) + celles de vos corrections.
    Apprentissage : chaque photo de corrections/<espèce>/ devient un exemple ; une image qui
    ressemble beaucoup à un exemple corrigé tire la prédiction vers son espèce (mémoire
    d'exemples, à la manière de Tip-Adapter). Pas d'entraînement long : apprendre() ne calcule
    que les nouvelles photos. Une espèce absente de la liste locale s'apprend de la même façon,
    et « Pas un oiseau » aussi (feuilles, écureuil, reflet...).
    """
    ALPHA, BETA = 20.0, 6.0     # poids et finesse de la mémoire d'exemples
    MARGE = 8.0                 # handicap des classes sans description (voir classer)
    POIDS_A_PRIORI = 1.0        # poids de la fréquence locale des espèces

    def __init__(self, dossier_modeles, latitude=None, longitude=None, dossier_corrections=None,
                 sur_message=None):
        self.dossier_modeles = Path(dossier_modeles)
        self.latitude, self.longitude = latitude, longitude
        self.dossier_corrections = Path(dossier_corrections) if dossier_corrections else None
        self.sur_message = sur_message or print
        self.modele = None
        self._verrou = threading.RLock()
        self.especes, self.noms = [], []
        self.exemples, self.etiquettes = None, np.zeros(0, int)
        self.nb_exemples = self.nb_especes_apprises = 0

    # --- chargement
    def charger(self):
        with self._verrou:
            if self.modele is not None:
                return
            import open_clip
            self.modele, _entrainement, self.pretraitement = open_clip.create_model_and_transforms(MODELE_BIOCLIP)
            self.tokenizer = open_clip.get_tokenizer(MODELE_BIOCLIP)
            self.appareil = appareil()
            self.modele.to(self.appareil).eval()
            self.especes = especes_locales(self.dossier_modeles, self.latitude, self.longitude, self.sur_message)
            self.textes = self._vecteurs_texte(self.especes)
            self.apprendre()

    def _encoder_textes(self, textes):
        import torch
        with torch.no_grad():
            v = self.modele.encode_text(self.tokenizer(textes).to(self.appareil)).float()
        return (v / v.norm(dim=-1, keepdim=True)).cpu().numpy()

    def _vecteurs_texte(self, especes):
        """Un vecteur par espèce (« a photo of Parus major (Great Tit). »), mis en cache."""
        cache = self.dossier_modeles / "bioclip_textes.npz"
        connus = dict(np.load(cache)) if cache.exists() else {}
        manquants = [e for e in especes if e["sci"] not in connus]
        if len(manquants) > 300:
            self.sur_message(_("Préparation de {n} espèces (une seule fois)...", n=len(manquants)))
        for i in range(0, len(manquants), 64):
            lot = manquants[i:i + 64]
            vecteurs = self._encoder_textes([f"a photo of {e['sci']} ({e['en']})." if e["en"]
                                             else f"a photo of {e['sci']}." for e in lot])
            connus.update({e["sci"]: v for e, v in zip(lot, vecteurs)})
        if manquants:
            self.dossier_modeles.mkdir(parents=True, exist_ok=True)
            np.savez(cache, **connus)
        if not especes:
            return np.zeros((0, 512), np.float32)
        return np.stack([connus[e["sci"]] for e in especes])

    def _texte_espece(self, nom):
        """Vecteur texte d'une espèce ajoutée par correction (nom français ou scientifique)."""
        if nom == PAS_UN_OISEAU:
            return None
        cle = cle_espece(nom)
        for sci, en, local in etiquettes_birdnet(self.dossier_modeles):
            if cle in (cle_espece(local), cle_espece(sci), cle_espece(en)):
                return self._encoder_textes([f"a photo of {sci} ({en})."])[0]
        return self._encoder_textes([f"a photo of a bird, {nom}."])[0]

    def _vecteur_image(self, image_pil):
        import torch
        with torch.no_grad():
            v = self.modele.encode_image(self.pretraitement(image_pil.convert("RGB"))[None].to(self.appareil)).float()
        return (v / v.norm(dim=-1, keepdim=True)).cpu().numpy()[0]

    # --- apprentissage sur les corrections
    def apprendre(self):
        """(Re)lit corrections/<espèce>/*.jpg. Renvoie (nb de photos, nb d'espèces)."""
        from PIL import Image
        with self._verrou:
            if self.modele is None:
                self.charger()
                return self.nb_exemples, self.nb_especes_apprises
            noms = [e["nom"] for e in self.especes]
            textes = list(self.textes)
            sans_texte = []                      # classes connues uniquement par leurs exemples
            index = {cle_espece(n): i for i, n in enumerate(noms)}
            vecteurs, etiquettes = [], []
            d = self.dossier_corrections
            if d and d.exists():
                cache = d / "exemples.npz"
                anciens = dict(np.load(cache)) if cache.exists() else {}
                gardes = {}
                for sous in sorted(p for p in d.iterdir() if p.is_dir()):
                    photos = sorted(sous.glob("*.jpg"))
                    if not photos:
                        continue
                    fichier_nom = sous / "nom.txt"
                    nom = fichier_nom.read_text(encoding="utf-8").strip() if fichier_nom.exists() \
                        else sous.name.replace("_", " ")
                    cle = cle_espece(nom)
                    if cle not in index:
                        index[cle] = len(noms)
                        noms.append(nom)
                        v = self._texte_espece(nom)
                        if v is None:
                            sans_texte.append(index[cle])
                            v = np.zeros(self.textes.shape[1], np.float32)
                        textes.append(v)
                    for p in photos:
                        k = f"{sous.name}|{p.name}|{p.stat().st_size}"
                        v = anciens.get(k)
                        if v is None:
                            v = self._vecteur_image(Image.open(p))
                        gardes[k] = v
                        vecteurs.append(v)
                        etiquettes.append(index[cle])
                if gardes or anciens:
                    np.savez(cache, **gardes)
            self.noms = noms
            # a priori : une espèce souvent observée ici est plus probable qu'une rareté
            # (log du nombre d'observations ; les espèces de vos corrections comptent comme courantes)
            obs = [e.get("obs", 0) for e in self.especes]
            courant = max(obs, default=0)
            self.a_priori = self.POIDS_A_PRIORI * np.log1p(np.array(obs + [courant] * (len(noms) - len(obs)), float))
            self.textes_classes = np.stack(textes) if textes else np.zeros((0, 512), np.float32)
            self.sans_texte = np.array(sans_texte, int)
            self.exemples = np.stack(vecteurs) if vecteurs else None
            self.etiquettes = np.array(etiquettes, int)
            self.nb_exemples, self.nb_especes_apprises = len(vecteurs), len(set(etiquettes))
            return self.nb_exemples, self.nb_especes_apprises

    # --- oiseau ou pas ? (seconde chance quand le détecteur d'objets ne voit rien)
    OISEAU = ["a photo of a bird.", "a photo of Aves."]
    AUTRES = ["a photo of a human face.", "a photo of a person.", "a photo of a hand.", "a photo of leaves.",
              "a photo of a tree branch.", "a photo of bird seeds.", "a photo of an empty room.", "a photo of a cat.",
              "a photo of a squirrel.", "a photo of a lizard.", "a photo of an insect.", "a photo of bird eggs.",
              "a dark blurry photo.", "a photo of a wall.", "a photo of an object."]

    def prob_oiseau(self, image_bgr):
        """Probabilité que l'image montre un oiseau (BioCLIP, zero-shot)."""
        from PIL import Image
        self.charger()
        with self._verrou:
            if getattr(self, "_textes_oiseau", None) is None:
                self._textes_oiseau = self._encoder_textes(self.OISEAU + self.AUTRES)
            f = self._vecteur_image(Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)))
            logits = 100.0 * self._textes_oiseau @ f
            p = np.exp(logits - logits.max())
            return float(p[:len(self.OISEAU)].sum() / p.sum())

    # --- reconnaissance
    def classer(self, image_bgr, top_k=3):
        """[(espece, probabilite)] des top_k espèces les plus probables."""
        from PIL import Image
        self.charger()
        with self._verrou:
            f = self._vecteur_image(Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)))
            logits = 100.0 * self.textes_classes @ f + self.a_priori
            if len(self.sans_texte):
                # classes connues seulement par leurs exemples (« Pas un oiseau »...) : un cran sous la
                # meilleure espèce, elles l'emportent si l'image ressemble vraiment à un exemple (cos > ~0,85)
                logits[self.sans_texte] = logits.max() - self.MARGE
            if self.exemples is not None:
                affinite = np.exp(-self.BETA * (1.0 - self.exemples @ f))
                for c in np.unique(self.etiquettes):
                    proches = np.sort(affinite[self.etiquettes == c])[-3:]   # 3 exemples les plus proches
                    logits[c] += self.ALPHA * proches.mean()
            p = np.exp(logits - logits.max())
            p /= p.sum()
            return [(self.noms[i], float(p[i])) for i in np.argsort(-p)[:top_k]]


class DetecteurOiseaux:
    """Trouve les oiseaux dans l'image (détecteur d'objets COCO, classe « bird »)."""

    def __init__(self, modele=MODELE_DETECTION, seuil=0.5, largeur=640):
        self.modele, self.seuil, self.largeur = modele, seuil, largeur
        self.pipe = None
        self._verrou = threading.Lock()

    def charger(self):
        with self._verrou:
            if self.pipe is None:
                from transformers import pipeline
                self.pipe = pipeline("object-detection", model=self.modele, device=appareil())

    def detecter(self, image_bgr):
        """Liste de (score, (x, y, l, h)) en pixels de l'image d'origine, du plus grand au plus petit."""
        self.charger()
        from PIL import Image
        e = min(1.0, self.largeur / image_bgr.shape[1])
        petite = cv2.resize(image_bgr, None, fx=e, fy=e) if e < 1 else image_bgr
        image = Image.fromarray(cv2.cvtColor(petite, cv2.COLOR_BGR2RGB))
        oiseaux = []
        for r in self.pipe(image, threshold=self.seuil):
            if r["label"] == "bird":
                b = r["box"]
                x, y = b["xmin"] / e, b["ymin"] / e
                oiseaux.append((float(r["score"]), (int(x), int(y), int(b["xmax"] / e - x), int(b["ymax"] / e - y))))
        return sorted(oiseaux, key=lambda o: o[1][2] * o[1][3], reverse=True)


def recadrer(image, boite, marge=0.15):
    """Recadrage carré autour d'une boîte (le modèle attend un oiseau centré)."""
    h, w = image.shape[:2]
    x, y, bw, bh = boite
    cote = min(int(max(bw, bh) * (1 + 2 * marge)), w, h)
    cx, cy = x + bw // 2, y + bh // 2
    x0 = max(0, min(w - cote, cx - cote // 2))
    y0 = max(0, min(h - cote, cy - cote // 2))
    return image[y0:y0 + cote, x0:x0 + cote]


# ------------------------------------------------------------------
#  Chants : BirdNET en continu sur le micro
# ------------------------------------------------------------------
class Ecoute:
    """Écoute le micro et reconnaît les chants (BirdNET v2.4, fenêtres de 3 s).

    Les détections sont gardées en mémoire (pour les associer aux visites),
    notées dans chants.csv (une ligne par espèce et par minute au plus) et
    signalées via sur_chant(espece, confiance).
    """
    FREQ = 48000
    FENETRE = 3.0

    def __init__(self, dossier_modeles, dossier_journal, seuil=0.6, latitude=None, longitude=None,
                 micro=None, sur_chant=None, sur_message=None):
        self.dossier_modeles = Path(dossier_modeles)
        self.dossier_journal = Path(dossier_journal)
        self.seuil, self.latitude, self.longitude, self.micro = seuil, latitude, longitude, micro
        self.sur_chant = sur_chant or (lambda e, c: None)
        self.sur_message = sur_message or print
        self.historique = deque(maxlen=2000)     # (horodatage, espece, confiance)
        self.dernier_note = {}
        self.niveau = 0.0                        # niveau sonore de la dernière fenêtre (contrôle du micro)
        self.memoire = deque(maxlen=60)          # (horodatage, 1 s de son à 48 kHz) : 1 minute
        self.complement = None                   # espèces absentes de BirdNET (chants_complement.py)
        self.arret = threading.Event()
        self.session = None
        self.fil = None

    # --- modèles
    @staticmethod
    def telecharger(dossier):
        """Télécharge BirdNET (ONNX + étiquettes) et les noms d'espèces traduits (projet BirdNET-Go)."""
        from huggingface_hub import hf_hub_download
        dossier = Path(dossier)
        dossier.mkdir(parents=True, exist_ok=True)
        for f in ("birdnet.onnx", "birdnet_data_model.onnx", "BirdNET_GLOBAL_6K_V2.4_Labels.txt"):
            if not (dossier / f).exists():
                (dossier / f).write_bytes(Path(hf_hub_download(DEPOT_BIRDNET, f)).read_bytes())
        for code in langues.LANGUES:
            local = fichier_etiquettes(dossier, code)
            if not local.exists():
                url = ("https://raw.githubusercontent.com/tphakala/birdnet-go/main/"
                       f"internal/classifier/data/labels/V2.4/{local.name}")
                try:
                    local.write_bytes(urllib.request.urlopen(url, timeout=30).read())
                except Exception:
                    pass   # noms anglais à défaut

    def charger(self):
        import onnxruntime as ort
        d = self.dossier_modeles
        modele = d / "birdnet.onnx"
        if (d / "chants_complement.npz").exists():
            # BirdNET + empreintes sonores pour reconnaître aussi les espèces apprises
            try:
                import chants_complement
                complement = chants_complement.Complement(d)
                if complement.distance_km(self.latitude, self.longitude) <= 500:   # appris pour cette région
                    modele = chants_complement.preparer_modele_empreintes(d)
                    self.complement = complement
                    self.sur_message(_("Chants : {n} espèces locales ajoutées à BirdNET", n=len(complement.noms) - 1))
            except Exception as e:
                self.complement = None
                self.sur_message(_("Complément des chants indisponible ({erreur})", erreur=type(e).__name__))
        self.session = ort.InferenceSession(str(modele), providers=["CPUExecutionProvider"])
        self.entree = self.session.get_inputs()[0].name
        etiquettes = etiquettes_birdnet(d)
        self.scientifiques = [e[0] for e in etiquettes]
        self.noms = [e[2] for e in etiquettes]
        self.autorises = self._filtre_geographique()

    def _filtre_geographique(self):
        """Espèces plausibles à cet endroit cette semaine (méta-modèle BirdNET), plus les espèces
        réellement observées autour (liste iNaturalist, utile là où BirdNET a peu de données,
        dans les îles par exemple). None = toutes."""
        if self.latitude is None or self.longitude is None:
            return None
        try:
            semaine = min(48, (datetime.now().timetuple().tm_yday - 1) // 7.6 + 1)
            p = probabilites_geo(self.dossier_modeles, self.latitude, self.longitude, [semaine])
            autorises = set(np.where(p >= 0.03)[0].tolist())
            locales = {e["sci"]: e["nom"] for e in especes_locales(self.dossier_modeles, self.latitude,
                                                                    self.longitude, self.sur_message)}
            for i, s in enumerate(self.scientifiques):
                if s in locales:
                    autorises.add(i)
                    self.noms[i] = locales[s]       # mêmes noms que la reconnaissance par l'image
            if self.complement is not None:         # espèces apprises : noms dans la langue de l'interface
                self.complement.noms = [locales.get(s, n) for s, n in zip(self.complement.sci, self.complement.noms)]
            self.sur_message(_("Chants : {n} espèces possibles ici cette semaine", n=len(autorises)))
            return autorises
        except Exception as e:
            self.sur_message(_("Filtre géographique indisponible ({erreur})", erreur=type(e).__name__))
            return None

    def analyser(self, signal):
        """signal : float32 mono 48 kHz, 3 s. Renvoie [(espece, nom_scientifique, confiance)] triés."""
        x = signal.astype(np.float32)[None, :]
        sorties = self.session.run(None, {self.entree: x})
        scores = np.asarray(sorties[0]).reshape(-1)
        if scores.min() < 0 or scores.max() > 1:          # logits -> probabilités
            scores = 1 / (1 + np.exp(-np.clip(scores, -15, 15)))
        res = [(self.noms[i], self.scientifiques[i], float(scores[i]))
               for i in np.where(scores >= self.seuil)[0]
               if self.autorises is None or int(i) in self.autorises]
        # BirdNET contient aussi des classes non-oiseaux (voix humaine, bruit, moteur, chien...)
        res = [r for r in res if not any(m in r[1].lower() for m in NON_OISEAUX)]
        if self.complement is not None and len(sorties) > 1:
            res += self.complement.analyser(sorties[1], self.seuil)
        return sorted(res, key=lambda r: -r[2])

    def extrait(self, debut, fin):
        """Son capté entre deux instants (au plus la dernière minute), float32 48 kHz, ou None."""
        morceaux = [s for t, s in list(self.memoire) if debut - timedelta(seconds=1) <= t <= fin]
        return np.concatenate(morceaux) if morceaux else None

    # --- capture
    def demarrer(self):
        self.arret.clear()
        self.fil = threading.Thread(target=self._executer, daemon=True)
        self.fil.start()

    def arreter(self):
        self.arret.set()

    def _executer(self):
        try:
            import sounddevice as sd
            if self.session is None:
                self.charger()
            assurer_journal(self.dossier_journal / "chants.csv", COLONNES_CHANTS)
            # capture à la fréquence native du micro (beaucoup de micros intégrés ne
            # renvoient que des zéros à 48 kHz), puis conversion en 48 kHz pour BirdNET
            appareil = self.micro if self.micro is not None else sd.default.device[0]
            freq = int(sd.query_devices(appareil, "input")["default_samplerate"])
            tampon = deque(maxlen=int(freq * self.FENETRE))
            file = deque()
            verrou = threading.Lock()
            cible = int(self.FREQ * self.FENETRE)

            def rappel(indata, frames, t, status):
                with verrou:
                    file.append(indata[:, 0].copy())

            with sd.InputStream(samplerate=freq, channels=1, dtype="float32", device=self.micro,
                                blocksize=int(freq * 0.25), callback=rappel):
                self.sur_message(_("Écoute des chants : micro actif ({freq} Hz)", freq=freq))
                prochaine = time.time() + self.FENETRE
                seconde = []
                while not self.arret.is_set():
                    time.sleep(0.1)
                    with verrou:
                        while file:
                            bloc = file.popleft()
                            tampon.extend(bloc)
                            seconde.append(bloc)
                    if sum(len(b) for b in seconde) >= freq:      # mémoire d'une minute, par secondes
                        s = np.concatenate(seconde)
                        if freq != self.FREQ:
                            s = np.interp(np.linspace(0, len(s) - 1, int(len(s) * self.FREQ / freq)),
                                          np.arange(len(s)), s).astype(np.float32)
                        self.memoire.append((datetime.now(), s))
                        seconde = []
                    if len(tampon) == tampon.maxlen and time.time() >= prochaine:
                        prochaine = time.time() + 1.5          # fenêtres glissantes, recouvrement 50 %
                        signal = np.fromiter(tampon, np.float32)
                        if freq != self.FREQ:
                            signal = np.interp(np.linspace(0, len(signal) - 1, cible),
                                               np.arange(len(signal)), signal).astype(np.float32)
                        self.niveau = float(np.sqrt(np.mean(signal ** 2)))
                        for espece, sci, conf in self.analyser(signal)[:3]:
                            self._noter(espece, sci, conf)
        except Exception as e:
            self.sur_message(_("Écoute des chants impossible : {erreur}", erreur=e))

    def _noter(self, espece, sci, conf):
        maintenant = datetime.now()
        self.historique.append((maintenant, espece, conf))
        self.sur_chant(espece, conf)
        dernier = self.dernier_note.get(espece)
        if dernier is None or (maintenant - dernier).total_seconds() > 60:
            self.dernier_note[espece] = maintenant
            ajouter_ligne(self.dossier_journal / "chants.csv", {
                "date": maintenant.strftime("%Y-%m-%d"), "heure": maintenant.strftime("%H:%M:%S"),
                "espece": espece, "nom_scientifique": sci, "confiance": f"{conf:.2f}"}, COLONNES_CHANTS)

    def entre(self, debut, fin):
        """Meilleure confiance par espèce entendue entre deux instants."""
        meilleurs = {}
        for t, espece, conf in list(self.historique):
            if debut <= t <= fin:
                meilleurs[espece] = max(conf, meilleurs.get(espece, 0))
        return sorted(meilleurs.items(), key=lambda kv: -kv[1])


# ------------------------------------------------------------------
#  Détection de mouvement
# ------------------------------------------------------------------
class DetecteurMouvement:
    def __init__(self, surface_min, largeur_analyse=480):
        self.fond = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=32, detectShadows=False)
        self.surface_min = surface_min
        self.largeur = largeur_analyse

    def analyser(self, image):
        """Renvoie la boîte (x, y, l, h) du plus grand objet en mouvement, en pixels de l'image d'origine."""
        echelle = self.largeur / image.shape[1]
        petite = cv2.resize(image, None, fx=echelle, fy=echelle)
        masque = self.fond.apply(cv2.GaussianBlur(petite, (5, 5), 0))
        masque = cv2.morphologyEx(masque, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        masque = cv2.dilate(masque, np.ones((7, 7), np.uint8), iterations=2)
        contours, _hierarchie = cv2.findContours(masque, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        plus_grand = max(contours, key=cv2.contourArea)
        if cv2.contourArea(plus_grand) < self.surface_min * petite.shape[0] * petite.shape[1]:
            return None
        x, y, w, h = cv2.boundingRect(plus_grand)
        return tuple(int(v / echelle) for v in (x, y, w, h))


# ------------------------------------------------------------------
#  Visite (un clip)
# ------------------------------------------------------------------
class Visite:
    def __init__(self, dossier, fps, taille, pre_images):
        self.debut = datetime.now()
        self.base = dossier / self.debut.strftime("%Y-%m-%d_%H-%M-%S")
        self.chemin_video = self.base.with_suffix(".mp4")
        self.video = cv2.VideoWriter(str(self.chemin_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, taille)
        for image in pre_images:
            self.video.write(image)
        self.scores = defaultdict(list)
        self.premiers = Counter()           # nb d'analyses où l'espèce arrive en tête
        self.meilleure = (0.0, None, None, None)  # (confiance, espèce, image, oiseau recadré)
        self.nb_images = len(pre_images)
        self.oiseaux_vus = 0                # analyses où un oiseau a été détecté
        self.photo_oiseau = (0.0, None, None)  # meilleure image avec oiseau (si pas de reconnaissance)

    def ecrire(self, image):
        self.video.write(image)
        self.nb_images += 1

    def ajouter_prediction(self, predictions, image, recadrage=None):
        for espece, score in predictions:
            self.scores[espece].append(score)
        espece, score = predictions[0]
        self.premiers[espece] += 1
        if score > self.meilleure[0]:
            self.meilleure = (score, espece, image.copy(), None if recadrage is None else recadrage.copy())

    def conclure(self, seuil):
        """Espèce retenue = vote sur toute la visite : elle doit arriver en tête
        sur au moins la moitié des analyses et atteindre le seuil au moins une fois."""
        self.video.release()
        if not self.scores:
            return "Inconnu", 0.0
        totaux = {e: sum(s) for e, s in self.scores.items()}
        espece = max(totaux, key=totaux.get)
        confiance = max(self.scores[espece])
        majoritaire = self.premiers[espece] >= sum(self.premiers.values()) / 2
        return (espece if majoritaire and confiance >= seuil else "Inconnu"), confiance


# ------------------------------------------------------------------
#  Moteur
# ------------------------------------------------------------------
class Surveillance:
    """Boucle caméra -> mouvement -> enregistrement -> filtre oiseau -> reconnaissance.

    seuil, surface, reconnaissance_active et filtre_oiseaux peuvent être modifiés
    pendant l'exécution. Rappels (appelés depuis le fil de la surveillance) :
      sur_image(vue_bgr, etat)  sur_visite(ligne_du_journal)  sur_message(texte)
    """

    def __init__(self, source, dossier, seuil=0.75, surface=0.01,
                 avant=3, apres=4, duree_max=120, analyse_toutes=0.5, reconnaissance=True,
                 reconnaisseur=None, sur_image=None, sur_visite=None, sur_message=None, temps_reel=False,
                 filtre_oiseaux=True, garder_sans_oiseau=False, detecteur_oiseaux=None, ecoute=None,
                 seuil_chant=0.7, menage_jours=60, menage_go=20.0):
        self.source = source_depuis_texte(source)
        self.flux_web = est_flux_web(self.source)    # le micro du PC n'entend pas ce nid lointain
        self.dossier = Path(dossier)
        self.seuil, self.surface = seuil, surface
        self.avant, self.apres, self.duree_max = avant, apres, duree_max
        self.analyse_toutes = analyse_toutes
        self.reconnaissance_active = reconnaissance
        self.reconnaisseur = reconnaisseur or Reconnaisseur(self.dossier / "modeles",
                                                            dossier_corrections=self.dossier / "corrections")
        self.filtre_oiseaux, self.garder_sans_oiseau = filtre_oiseaux, garder_sans_oiseau
        self.detecteur_oiseaux = detecteur_oiseaux or DetecteurOiseaux()
        self.ecoute, self.seuil_chant = ecoute, seuil_chant
        self.seuil_oiseau_bioclip = 0.85
        self.menage_jours, self.menage_go = menage_jours, menage_go
        self.sur_image = sur_image or (lambda vue, etat: None)
        self.sur_visite = sur_visite or (lambda ligne: None)
        self.sur_message = sur_message or print
        self.temps_reel = temps_reel   # fichier vidéo lu à sa vitesse normale (affichage)
        self.arret = threading.Event()

    def arreter(self):
        self.arret.set()

    def _menage(self):
        n = nettoyer(self.dossier, self.menage_jours, self.menage_go)
        if n:
            self.sur_message(_("Ménage : anciens clips effacés : {n}", n=n))

    def _garder_son(self, visite, espece):
        """Espèce sûre à l'image mais inconnue de BirdNET (endémique...) : le son de la visite est
        gardé dans chants_perso/<espèce>/ ; « Compléter les chants » apprendra ensuite son chant."""
        e = self.ecoute
        if e is None or not getattr(e, "scientifiques", None):
            return
        sci = next((x["sci"] for x in getattr(self.reconnaisseur, "especes", []) if x["nom"] == espece), None)
        if sci is None or sci in e.scientifiques:
            return
        son = e.extrait(visite.debut - timedelta(seconds=self.avant), datetime.now())
        if son is None or len(son) < 3 * Ecoute.FREQ or float(np.sqrt(np.mean(son ** 2))) < 2e-4:
            return
        try:
            import soundfile as sf
            d = self.dossier / "chants_perso" / nom_fichier(espece)
            d.mkdir(parents=True, exist_ok=True)
            (d / "nom.txt").write_text(espece, encoding="utf-8")
            sf.write(str(d / f"{visite.base.name}.wav"), son, Ecoute.FREQ)
            self.sur_message(_("Son de la visite gardé pour apprendre le chant : {espece}", espece=espece))
        except Exception as ex:
            self.sur_message(_("Son de la visite non gardé ({erreur})", erreur=type(ex).__name__))

    def _terminer(self, visite, fps, journal):
        duree = visite.nb_images / fps
        espece, confiance = visite.conclure(self.seuil)

        # « Pas un oiseau » : appris de vos corrections (feuilles, écureuil, reflet...)
        sans_oiseau = (self.filtre_oiseaux and visite.oiseaux_vus < 1) or espece == PAS_UN_OISEAU
        if sans_oiseau and not self.garder_sans_oiseau:
            try:
                visite.chemin_video.unlink()
            except OSError:
                pass
            self.sur_message(_("Mouvement sans oiseau ({duree} s) : clip effacé", duree=f"{duree:.0f}"))
            return

        source = "image" if espece != "Inconnu" else ""
        ecoute = None if self.flux_web else self.ecoute
        chants = ecoute.entre(visite.debut - timedelta(seconds=self.avant), datetime.now()) if ecoute else []
        if chants:
            meilleur, conf_chant = chants[0]
            if espece == "Inconnu" and conf_chant >= self.seuil_chant:
                espece, confiance, source = meilleur, conf_chant, "chant"
            elif cle_espece(meilleur) == cle_espece(espece):
                source, confiance = "image+chant", max(confiance, conf_chant)

        if source.startswith("image") and confiance >= 0.9 and ecoute:
            self._garder_son(visite, espece)
        video = visite.chemin_video.with_name(f"{visite.base.name}_{nom_fichier(espece)}.mp4")
        visite.chemin_video.rename(video)
        if visite.meilleure[2] is not None:
            image_photo, image_oiseau = visite.meilleure[2], visite.meilleure[3]
        else:
            image_photo, image_oiseau = visite.photo_oiseau[1], visite.photo_oiseau[2]
        photo = None
        if image_photo is not None:
            photo = video.with_suffix(".jpg")
            cv2.imwrite(str(photo), image_photo)
            if image_oiseau is not None:     # sert d'exemple si la visite est corrigée
                cv2.imwrite(str(photo.with_name(photo.stem + "_oiseau.jpg")), image_oiseau)
        ligne = {"date": visite.debut.strftime("%Y-%m-%d"), "heure": visite.debut.strftime("%H:%M:%S"),
                 "duree_s": f"{duree:.0f}", "espece": espece, "confiance": f"{confiance:.2f}",
                 "video": video.name, "photo": photo.name if photo else "", "source": source,
                 "chants": ", ".join(f"{e} {c:.0%}" for e, c in chants[:3]), "corrige": ""}
        ajouter_ligne(journal, ligne, COLONNES)
        garder_dans_galerie(self.dossier, ligne)
        self.sur_message(_("Fin de visite : {espece} ({conf}), {duree} s",
                           espece=_(espece) if espece == "Inconnu" else espece,
                           conf=f"{confiance:.0%}", duree=f"{duree:.0f}"))
        self.sur_visite(ligne)
        self._menage()

    def executer(self):
        est_fichier = isinstance(self.source, str) and Path(self.source).is_file()
        self.dossier.mkdir(parents=True, exist_ok=True)
        journal = self.dossier / "visites.csv"
        assurer_journal(journal, COLONNES)
        n = effacer_clips_interrompus(self.dossier)
        if n:
            self.sur_message(_("Clips interrompus illisibles effacés : {n}", n=n))
        self._menage()

        camera, image = ouvrir_source(self.source)
        if camera is None:
            self.sur_message(_("La source vidéo ne renvoie aucune image : {source} (caméra utilisée par une autre "
                               "application, ou accès refusé dans Paramètres › Confidentialité › Caméra)",
                               source=self.source))
            return False
        fps = camera.get(cv2.CAP_PROP_FPS)
        fps = fps if 1 < fps < 120 else 15
        taille = (image.shape[1], image.shape[0])
        self.sur_message(_("Source ouverte : {largeur}x{hauteur} à {fps} i/s", largeur=taille[0], hauteur=taille[1],
                           fps=f"{fps:.0f}"))

        detecteur = DetecteurMouvement(self.surface)
        tampon = deque(maxlen=int(self.avant * fps))
        visite = None
        dernier_mouvement = derniere_analyse = 0.0
        nb_lues = 0
        demarrage = 0.0 if est_fichier else time.time()
        etiquette, oiseaux = "", []
        t_fps, n_fps, fps_mesure = time.time(), 0, 0.0

        try:
            while not self.arret.is_set():
                ok, image = camera.read()
                if not ok:
                    if est_fichier:
                        break
                    if visite is not None:      # ne pas laisser un clip ouvert pendant la panne
                        self._terminer(visite, fps, journal)
                        visite, etiquette, oiseaux = None, "", []
                    self.sur_message(_("Flux interrompu, nouvelle tentative dans 2 s ..."))
                    camera.release()
                    self.arret.wait(2)
                    nouvelle, image = ouvrir_source(self.source)
                    if nouvelle is None:
                        camera = cv2.VideoCapture()      # capture vide : read() échoue, on réessaie
                        continue
                    camera = nouvelle
                    if (image.shape[1], image.shape[0]) != taille:
                        image = cv2.resize(image, taille)
                nb_lues += 1
                maintenant = nb_lues / fps if est_fichier else time.time()
                if est_fichier and self.temps_reel:
                    if nb_lues == 1:
                        t_lecture = time.time()
                    attente = t_lecture + nb_lues / fps - time.time()
                    if attente > 0:
                        time.sleep(attente)
                detecteur.surface_min = self.surface
                boite = detecteur.analyser(image)
                if maintenant - demarrage < 3:   # le modèle de fond apprend la scène
                    boite = None

                if boite is not None:
                    dernier_mouvement = maintenant
                    if visite is None:
                        visite = Visite(self.dossier, fps, taille, list(tampon))
                        self.sur_message(_("Mouvement : début d'enregistrement"))

                if visite is not None:
                    visite.ecrire(image)
                    if maintenant - derniere_analyse >= self.analyse_toutes and (boite is not None or oiseaux):
                        derniere_analyse = maintenant
                        if self.filtre_oiseaux:
                            oiseaux = self.detecteur_oiseaux.detecter(image)
                            confirmation = 1.0
                            if not oiseaux and boite is not None:
                                # le détecteur rate certains oiseaux (pose, contre-jour...) : BioCLIP juge
                                # la zone en mouvement ; il faut deux avis sûrs pour valider une visite
                                p = self.reconnaisseur.prob_oiseau(recadrer(image, boite, 0.2))
                                if p >= self.seuil_oiseau_bioclip:
                                    oiseaux, confirmation = [(p, boite)], 0.5
                            cible = oiseaux[0][1] if oiseaux else None
                            if oiseaux:
                                visite.oiseaux_vus += confirmation
                                dernier_mouvement = maintenant      # un oiseau immobile prolonge la visite
                                if oiseaux[0][0] > visite.photo_oiseau[0]:
                                    visite.photo_oiseau = (oiseaux[0][0], image.copy(), recadrer(image, cible).copy())
                        else:
                            cible = boite
                        if self.reconnaissance_active and cible is not None:
                            oiseau = recadrer(image, cible)
                            predictions = self.reconnaisseur.classer(oiseau)
                            visite.ajouter_prediction(predictions, image, oiseau)
                            etiquette = f"{predictions[0][0]}  {predictions[0][1]:.0%}"
                    if maintenant - dernier_mouvement > self.apres or visite.nb_images / fps > self.duree_max:
                        self._terminer(visite, fps, journal)
                        visite, etiquette, oiseaux = None, "", []
                else:
                    tampon.append(image)

                n_fps += 1
                if time.time() - t_fps >= 1:
                    fps_mesure, t_fps, n_fps = n_fps / (time.time() - t_fps), time.time(), 0
                self.sur_image(image, {"boite": boite, "oiseaux": [o[1] for o in oiseaux],
                                       "enregistrement": visite is not None, "etiquette": etiquette,
                                       "fps": fps_mesure, "duree": visite.nb_images / fps if visite else 0})
        finally:
            if visite is not None:
                self._terminer(visite, fps, journal)
            camera.release()
        return True


# ------------------------------------------------------------------
#  Ligne de commande
# ------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Becquée : enregistrement + reconnaissance des oiseaux")
    p.add_argument("--source", default="0", help="index webcam (0, 1...), URL du flux du smartphone, "
                                                 "page d'une caméra en direct (YouTube...), ou fichier vidéo")
    p.add_argument("--dossier", default="visites", help="dossier des clips, photos et du journal")
    p.add_argument("--modeles", default=str(Path(__file__).resolve().parent / "modeles"),
                   help="dossier des modèles et listes d'espèces (BirdNET, caches)")
    p.add_argument("--position", nargs=2, type=float, metavar=("LAT", "LON"),
                   help="position de la mangeoire : choisit les espèces locales (image et chants)")
    p.add_argument("--seuil", type=float, default=0.75,
                   help="confiance minimale (meilleure image) pour nommer l'espèce, en plus du vote majoritaire")
    p.add_argument("--surface", type=float, default=0.01, help="surface min. en mouvement (fraction de l'image)")
    p.add_argument("--avant", type=float, default=3, help="secondes gardées avant le mouvement")
    p.add_argument("--apres", type=float, default=4, help="secondes sans mouvement avant de couper le clip")
    p.add_argument("--duree-max", type=float, default=120, help="durée max. d'un clip (s)")
    p.add_argument("--analyse-toutes", type=float, default=0.5, help="intervalle entre deux analyses (s)")
    p.add_argument("--sans-reconnaissance", action="store_true", help="enregistre seulement")
    p.add_argument("--sans-filtre", action="store_true", help="garde aussi les mouvements sans oiseau")
    p.add_argument("--chants", action="store_true", help="active l'écoute des chants (BirdNET)")
    p.add_argument("--menage-jours", type=float, default=60, help="efface les clips plus vieux (0 = jamais)")
    p.add_argument("--menage-go", type=float, default=20, help="taille max. du dossier en Go (0 = illimité)")
    p.add_argument("--apercu", action="store_true", help="affiche la vidéo en direct (q, Échap ou croix pour quitter)")
    args = p.parse_args()

    def message(texte):
        print(f"[{datetime.now():%H:%M:%S}] {texte}", flush=True)

    lat, lon = args.position if args.position else (None, None)
    Ecoute.telecharger(args.modeles)      # étiquettes et méta-modèle BirdNET servent aussi à l'image
    ecoute = None
    if args.chants:
        ecoute = Ecoute(args.modeles, args.dossier, latitude=lat, longitude=lon,
                        sur_chant=lambda e, c: message(f"Chant : {e} ({c:.0%})"), sur_message=message)
        Path(args.dossier).mkdir(parents=True, exist_ok=True)
        ecoute.demarrer()

    reconnaisseur = Reconnaisseur(args.modeles, lat, lon, Path(args.dossier) / "corrections", sur_message=message)
    s = Surveillance(args.source, args.dossier, args.seuil, args.surface, args.avant,
                     args.apres, args.duree_max, args.analyse_toutes, not args.sans_reconnaissance,
                     reconnaisseur=reconnaisseur, sur_message=message, filtre_oiseaux=not args.sans_filtre,
                     ecoute=ecoute, menage_jours=args.menage_jours, menage_go=args.menage_go)

    if args.apercu:
        def apercu(image, etat):
            vue = image.copy()
            if etat["boite"] is not None:
                x, y, w, h = etat["boite"]
                cv2.rectangle(vue, (x, y), (x + w, y + h), (0, 255, 0), 1)
            for x, y, w, h in etat["oiseaux"]:
                cv2.rectangle(vue, (x, y), (x + w, y + h), (0, 200, 255), 2)
            if etat["enregistrement"]:
                cv2.circle(vue, (25, 25), 10, (0, 0, 255), -1)
                cv2.putText(vue, etat["etiquette"], (45, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.imshow("Mangeoire", vue)
            touche = cv2.waitKey(1) & 0xFF
            # q, Échap, ou la croix de la fenêtre arrêtent le programme
            if touche in (ord("q"), 27) or cv2.getWindowProperty("Mangeoire", cv2.WND_PROP_VISIBLE) < 1:
                s.arreter()
        s.sur_image = apercu

    try:
        s.executer()
    except KeyboardInterrupt:
        pass
    finally:
        if ecoute:
            ecoute.arreter()
        cv2.destroyAllWindows()
    resume = Counter(l["espece"] for l in lire_journal(args.dossier))
    if resume:
        print("\nVisites enregistrées :")
        for espece, n in resume.most_common():
            print(f"  {espece:<25} {n}")


if __name__ == "__main__":
    main()
