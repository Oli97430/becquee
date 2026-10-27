"""
Becquée — compléter BirdNET avec les espèces locales qu'il ne connaît pas.

BirdNET reconnaît ~6 000 espèces, mais pas toutes : beaucoup d'endémiques (îles,
montagnes tropicales...) manquent. Pour chacune des espèces observées autour de la
mangeoire (liste iNaturalist) et absentes de BirdNET, ce module :

  1. rassemble des enregistrements : iNaturalist (sans clé), xeno-canto (clé API
     gratuite, facultative) et vos propres enregistrements, rangés dans
     chants_perso/<Nom de l'espèce>/ (wav, mp3, m4a, ogg, flac) ;
  2. découpe chaque enregistrement en fenêtres de 3 s et calcule l'« empreinte
     sonore » BirdNET de chacune (vecteur de 1 024 valeurs, couche avant la décision) ;
  3. entraîne un petit classifieur sur ces empreintes (méthode des « classifieurs
     personnalisés » de BirdNET), avec une classe « autre » faite des chants des
     espèces locales déjà connues et des bruits de fond ;
  4. l'évalue en laissant de côté des enregistrements entiers, puis l'enregistre
     dans modeles/chants_complement.npz, que l'écoute utilise ensuite.

Utilisation : Réglages › « Compléter les chants », ou
  python chants_complement.py --position -21.1 55.5 [--cle-xeno-canto CLE]
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np

import mangeoire_cam as m
from langues import _

FICHIER = "chants_complement.npz"
MODELE_EMPREINTES = "birdnet_empreintes.onnx"
COUCHE_EMPREINTE = "model/GLOBAL_AVG_POOL/Mean_reduced_0"
AUTRE = "(autre)"
FREQ, FENETRE = 48000, 144000
EXTENSIONS = (".wav", ".mp3", ".m4a", ".ogg", ".oga", ".flac", ".aac", ".opus")


# ------------------------------------------------------------------ empreintes BirdNET
def preparer_modele_empreintes(dossier_modeles):
    """Copie de BirdNET qui renvoie aussi l'empreinte (créée une fois, nécessite le paquet onnx)."""
    d = Path(dossier_modeles)
    cible = d / MODELE_EMPREINTES
    if not cible.exists():
        import onnx
        modele = onnx.load(str(d / "birdnet.onnx"))
        modele.graph.output.append(onnx.helper.make_tensor_value_info(COUCHE_EMPREINTE, onnx.TensorProto.FLOAT, None))
        onnx.save(modele, str(cible))
    return cible


class Empreintes:
    def __init__(self, dossier_modeles):
        import onnxruntime as ort
        self.session = ort.InferenceSession(str(preparer_modele_empreintes(dossier_modeles)),
                                            providers=["CPUExecutionProvider"])
        self.entree = self.session.get_inputs()[0].name

    def calculer(self, fenetres, lot=16):
        """fenetres (n, 144000) -> (scores BirdNET (n, 6522), empreintes (n, 1024))"""
        scores, empreintes = [], []
        for i in range(0, len(fenetres), lot):
            s, e = self.session.run(None, {self.entree: np.asarray(fenetres[i:i + lot], np.float32)})
            scores.append(s)
            empreintes.append(e.reshape(len(e), -1))
        return np.concatenate(scores), np.concatenate(empreintes)


# ------------------------------------------------------------------ audio
def decoder(chemin, max_s=120):
    """Fichier audio quelconque -> signal mono float32 à 48 kHz (PyAV / ffmpeg)."""
    import av
    morceaux, total = [], 0
    with av.open(str(chemin)) as conteneur:
        flux = conteneur.streams.audio[0]
        reech = av.AudioResampler(format="flt", layout="mono", rate=FREQ)
        for paquet in conteneur.decode(flux):
            for trame in reech.resample(paquet):
                a = trame.to_ndarray().reshape(-1)
                morceaux.append(a)
                total += len(a)
            if total >= max_s * FREQ:
                break
    return np.concatenate(morceaux).astype(np.float32) if morceaux else np.zeros(0, np.float32)


def fenetres(signal, pas=FENETRE // 2):
    """Fenêtres de 3 s (recouvrement 50 %) et leur énergie dans la bande des chants (1-10 kHz)."""
    if len(signal) < FENETRE:
        signal = np.pad(signal, (0, FENETRE - len(signal)))
    debuts = range(0, len(signal) - FENETRE + 1, pas)
    f = np.stack([signal[d:d + FENETRE] for d in debuts])
    spectre = np.abs(np.fft.rfft(f, axis=1))
    frequences = np.fft.rfftfreq(FENETRE, 1 / FREQ)
    bande = (frequences >= 1000) & (frequences <= 10000)
    return f, np.sqrt((spectre[:, bande] ** 2).mean(axis=1))


# ------------------------------------------------------------------ sources d'enregistrements
def _json(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=m.AGENT), timeout=40))


def sons_inaturalist(sci, maxi=40):
    """[(identifiant, url)] des sons d'observations iNaturalist de l'espèce."""
    res, page = [], 1
    while len(res) < maxi:
        q = urllib.parse.urlencode({"taxon_name": sci, "sounds": "true", "per_page": 100, "page": page,
                                    "order_by": "votes"})
        r = _json("https://api.inaturalist.org/v1/observations?" + q)
        for obs in r["results"]:
            for s in obs.get("sounds") or []:
                if s.get("file_url"):
                    res.append((f"inat{s['id']}", s["file_url"]))
        if page * 100 >= r["total_results"]:
            break
        page += 1
        time.sleep(1)
    return res[:maxi]


def sons_xeno_canto(sci, cle, maxi=40):
    """[(identifiant, url)] des enregistrements xeno-canto (API v3, clé gratuite), meilleure qualité d'abord."""
    if not cle:
        return []
    q = urllib.parse.urlencode({"query": f'sp:"{sci}"', "key": cle, "per_page": 200})
    r = _json("https://xeno-canto.org/api/3/recordings?" + q)
    enr = sorted(r.get("recordings", []), key=lambda e: e.get("q", "E"))
    return [(f"xc{e['id']}", e["file"]) for e in enr if e.get("file")][:maxi]


def telecharger(sons, dossier, sur_message=print):
    dossier.mkdir(parents=True, exist_ok=True)
    fichiers = []
    for ident, url in sons:
        deja = list(dossier.glob(f"{ident}.*"))
        if deja:
            fichiers.append(deja[0])
            continue
        ext = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".mp3"
        cible = dossier / f"{ident}{ext}"
        try:
            cible.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=m.AGENT), timeout=60).read())
            fichiers.append(cible)
        except Exception as e:
            sur_message(_("  téléchargement impossible ({erreur}) : {url}", erreur=type(e).__name__, url=url))
        time.sleep(0.5)
    return fichiers


# ------------------------------------------------------------------ apprentissage
def _entrainer(X, y, nb_classes, poids_l2=1e-3, iterations=400):
    """Régression logistique multinomiale (PyTorch, classes équilibrées) -> (W, b)."""
    import torch
    Xt, yt = torch.tensor(X, dtype=torch.float32), torch.tensor(y)
    comptes = np.bincount(y, minlength=nb_classes).astype(float)
    poids = torch.tensor(len(y) / (nb_classes * np.maximum(comptes, 1)), dtype=torch.float32)
    lin = torch.nn.Linear(X.shape[1], nb_classes)
    opt = torch.optim.Adam(lin.parameters(), lr=0.01, weight_decay=poids_l2)
    perte = torch.nn.CrossEntropyLoss(weight=poids)
    for _ in range(iterations):
        opt.zero_grad()
        perte(lin(Xt), yt).backward()
        opt.step()
    return lin.weight.detach().numpy(), lin.bias.detach().numpy()


def _probas(X, W, b):
    z = X @ W.T + b
    p = np.exp(z - z.max(axis=1, keepdims=True))
    return p / p.sum(axis=1, keepdims=True)


def completer(dossier_modeles, latitude, longitude, cle_xeno_canto="", dossier_perso=None,
              sur_message=print, max_par_espece=40, seuil=0.6):
    """Entraîne le complément pour les espèces locales absentes de BirdNET. Renvoie le résumé par espèce."""
    d = Path(dossier_modeles)
    connues = {sci for sci, _, _ in m.etiquettes_birdnet(d)}
    locales = m.especes_locales(d, latitude, longitude, sur_message)
    manquantes = [e for e in locales if e["sci"] not in connues]
    sur_message(_("{n} espèces locales absentes de BirdNET", n=len(manquantes)))
    emp = Empreintes(d)
    cache = d / "chants"

    def empreintes_fichier(fichier):
        """Empreintes des fenêtres chantées (et de quelques fenêtres de fond) d'un enregistrement, en cache."""
        c = fichier.with_suffix(".npz")
        if c.exists():
            z = np.load(c)
            return z["chant"], z["fond"]
        try:
            sig = decoder(fichier)
        except Exception as e:
            sur_message(_("  illisible ({erreur}) : {fichier}", erreur=type(e).__name__, fichier=fichier.name))
            return np.zeros((0, 1024)), np.zeros((0, 1024))
        if len(sig) < FREQ:
            return np.zeros((0, 1024)), np.zeros((0, 1024))
        f, energie = fenetres(sig)
        e = emp.calculer(f)[1]
        ordre = np.argsort(-energie)
        seuil_e = max(np.median(energie) * 1.3, 1e-6)
        chant = [i for i in ordre if energie[i] >= seuil_e][:30] or list(ordre[:max(1, len(ordre) // 3)])
        fond = [i for i in ordre[::-1] if i not in chant][:4]
        np.savez(c, chant=e[chant], fond=e[fond] if fond else np.zeros((0, e.shape[1])))
        return e[chant], e[fond] if fond else np.zeros((0, e.shape[1]))

    # --- espèces à apprendre
    classes, X, y, groupes, resume = [], [], [], [], {}
    for esp in manquantes:
        sons = []
        try:
            sons += sons_inaturalist(esp["sci"], max_par_espece)
        except Exception as e:
            sur_message(_("  iNaturalist indisponible ({erreur})", erreur=type(e).__name__))
        try:
            sons += sons_xeno_canto(esp["sci"], cle_xeno_canto, max_par_espece)
        except Exception as e:
            sur_message(_("  xeno-canto indisponible ({erreur}) : clé valide ?", erreur=type(e).__name__))
        fichiers = telecharger(sons, cache / m.nom_fichier(esp["sci"]), sur_message)
        if dossier_perso:
            for sous in Path(dossier_perso).glob("*"):
                nom_dossier = (sous / "nom.txt").read_text(encoding="utf-8").strip() if (sous / "nom.txt").exists() \
                    else sous.name.replace("_", " ")
                if sous.is_dir() and m.cle_espece(nom_dossier) in (m.cle_espece(esp["nom"]), m.cle_espece(esp["sci"]),
                                                                   m.cle_espece(esp.get("en", ""))):
                    fichiers += [p for p in sous.iterdir() if p.suffix.lower() in EXTENSIONS]
        if not fichiers:
            resume[esp["nom"]] = {"sci": esp["sci"], "enregistrements": 0}
            continue
        c = len(classes)
        n_fen = 0
        for f in fichiers:
            chant = empreintes_fichier(f)[0]
            X += list(chant); y += [c] * len(chant); groupes += [str(f)] * len(chant)
            n_fen += len(chant)
        if n_fen == 0:
            resume[esp["nom"]] = {"sci": esp["sci"], "enregistrements": 0}
            continue
        classes.append(esp)
        resume[esp["nom"]] = {"sci": esp["sci"], "enregistrements": len(fichiers), "fenetres": n_fen}
        sur_message(_("{espece} : {n} enregistrement(s), {f} fenêtres", espece=esp["nom"], n=len(fichiers), f=n_fen))
    if not classes:
        sur_message(_("Aucun enregistrement trouvé : rien à apprendre"))
        return resume

    # --- classe « autre » : chants des espèces locales que BirdNET connaît déjà + bruits de fond
    autre = len(classes)
    for esp in [e for e in locales if e["sci"] in connues][:25]:
        try:
            fichiers = telecharger(sons_inaturalist(esp["sci"], 5), cache / m.nom_fichier(esp["sci"]), sur_message)
        except Exception:
            continue
        for f in fichiers:
            chant, fond = empreintes_fichier(f)
            X += list(chant) + list(fond); y += [autre] * (len(chant) + len(fond)); groupes += [str(f)] * (len(chant) + len(fond))
    for f in sorted({g for g, c in zip(groupes, y) if c < autre}):     # fonds des enregistrements d'endémiques
        fond = empreintes_fichier(Path(f))[1]
        X += list(fond); y += [autre] * len(fond); groupes += [f] * len(fond)
    X, y, groupes = np.array(X, np.float32), np.array(y), np.array(groupes)
    moyenne, ecart = X.mean(axis=0), X.std(axis=0) + 1e-6
    Xn = (X - moyenne) / ecart

    # --- évaluation : validation croisée en retirant des enregistrements entiers (jamais entendus
    # pendant l'entraînement), puis choix du seuil qui garde les fausses alertes sous 1 %
    sur_message(_("Évaluation (enregistrements jamais entendus)..."))
    enregistrements = sorted(set(groupes))
    rng = np.random.default_rng(0)
    rng.shuffle(enregistrements)
    proba = np.zeros((len(y), autre + 1))
    for i in range(6):
        test = np.isin(groupes, enregistrements[i::6])
        W, b = _entrainer(Xn[~test], y[~test], autre + 1, iterations=250)
        proba[test] = _probas(Xn[test], W, b)
    meilleure = proba[:, :autre].max(axis=1)
    choix = proba[:, :autre].argmax(axis=1)
    est_autre = y == autre
    seuil_retenu, taux = 0.99, 0.0
    for s in (0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.97, 0.99):
        taux = float((meilleure[est_autre] >= s).mean())
        if taux <= 0.01:
            seuil_retenu = s
            break
    seuil_retenu = max(seuil_retenu, seuil)
    taux = float((meilleure[est_autre] >= seuil_retenu).mean())
    for c, esp in enumerate(classes):
        enr = sorted(set(groupes[y == c]))
        trouves = sum(bool(((choix == c) & (meilleure >= seuil_retenu) & (groupes == g)).any()) for g in enr)
        resume[esp["nom"]]["evaluation"] = f"{trouves}/{len(enr)}"
        resume[esp["nom"]]["rappel"] = trouves / len(enr)

    W, b = _entrainer(Xn, y, autre + 1)
    # « noms » : noms dans la langue de l'apprentissage (l'écoute les retraduit selon la langue choisie)
    np.savez(Path(d) / FICHIER, W=W, b=b, moyenne=moyenne, ecart=ecart, seuil=np.array(seuil_retenu),
             sci=np.array([e["sci"] for e in classes] + [AUTRE]), noms=np.array([e["nom"] for e in classes] + [AUTRE]),
             enregistrements=np.array([resume[e["nom"]]["enregistrements"] for e in classes] + [0]),
             position=np.array([latitude, longitude]), date=np.array(datetime.now().isoformat(timespec="minutes")),
             fausses_alertes=np.array(taux))
    sur_message(_("Complément des chants : {n} espèces apprises, seuil {seuil}, fausses alertes {fa} sur {t} fenêtres "
                  "d'autres oiseaux et de fond", n=len(classes), seuil=f"{seuil_retenu:.0%}", fa=f"{taux:.1%}",
                  t=int(est_autre.sum())))
    resume["_seuil"], resume["_fausses_alertes"] = seuil_retenu, taux
    return resume


class Complement:
    """Utilisé par l'écoute : probabilités des espèces apprises à partir des empreintes BirdNET."""

    def __init__(self, dossier_modeles):
        z = np.load(Path(dossier_modeles) / FICHIER)
        self.W, self.b, self.moyenne, self.ecart = z["W"], z["b"], z["moyenne"], z["ecart"]
        self.sci = [str(s) for s in z["sci"]]
        self.noms = [str(s) for s in (z["noms"] if "noms" in z else z["fr"])]     # ancien format : « fr »
        self.seuil = float(z["seuil"]) if "seuil" in z else 0.9     # calibré : < 1 % de fausses alertes
        self.position = tuple(float(v) for v in z["position"]) if "position" in z else None

    def distance_km(self, latitude, longitude):
        """Distance entre la mangeoire et l'endroit pour lequel le complément a été appris."""
        if self.position is None or latitude is None or longitude is None:
            return 0.0
        la1, lo1, la2, lo2 = map(np.radians, (*self.position, latitude, longitude))
        h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
        return float(6371 * 2 * np.arcsin(np.sqrt(h)))

    def analyser(self, empreinte, seuil):
        """[(nom, nom_scientifique, probabilité)] des espèces apprises au-dessus du seuil."""
        seuil = max(seuil, self.seuil)
        p = _probas(((np.asarray(empreinte).reshape(1, -1) - self.moyenne) / self.ecart), self.W, self.b)[0]
        return [(self.noms[i], self.sci[i], float(p[i])) for i in range(len(p) - 1) if p[i] >= seuil]


def main():
    a = argparse.ArgumentParser(description="Apprendre les chants des espèces locales absentes de BirdNET")
    a.add_argument("--position", nargs=2, type=float, required=True, metavar=("LAT", "LON"))
    a.add_argument("--modeles", default=str(Path(__file__).resolve().parent / "modeles"))
    a.add_argument("--cle-xeno-canto", default="", help="clé API xeno-canto (gratuite, facultative)")
    a.add_argument("--perso", help="dossier de vos enregistrements : <dossier>/<Nom de l'espèce>/*.wav|mp3|m4a...")
    args = a.parse_args()
    resume = completer(args.modeles, *args.position, args.cle_xeno_canto, args.perso)
    print(json.dumps(resume, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
