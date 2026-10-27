"""
Becquée — la mangeoire qui reconnaît ses visiteurs (application de bureau).

Vidéo en direct, enregistrement automatique des visites (seulement s'il y a
un oiseau), reconnaissance des espèces par l'image (BioCLIP, espèces locales
partout dans le monde) et par le chant (BirdNET), correction manuelle dont
l'application apprend, statistiques du jour et historique avec vignettes.
"""

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageTk

import langues
from langues import LANGUES, _
from mangeoire_cam import (PAS_UN_OISEAU, DetecteurOiseaux, Ecoute, Reconnaisseur, Surveillance,
                           chercher_lieu, cle_espece, construire_galerie, corriger_visite, lire_galerie,
                           lire_journal)

ICI = Path(__file__).resolve().parent
MODELES = ICI / "modeles"
if (ICI / "hf_cache").is_dir():     # version installée : modèles livrés avec l'installateur
    os.environ.setdefault("HF_HOME", str(ICI / "hf_cache"))
CONFIG = Path.home() / ".becquee.json"
DEFAUTS = {
    "langue": None,             # None = langue de Windows au premier lancement (voir langues.py)
    "source": "0",
    "dossier": str(Path.home() / "Videos" / "Becquee"),
    "seuil": 0.75,
    "sensibilite": 6,           # 1 (peu sensible) .. 10 (très sensible)
    "reconnaissance": True,
    "filtre_oiseaux": True,     # efface les mouvements sans oiseau
    "garder_sans_oiseau": False,
    "ecoute": True,             # BirdNET sur le micro
    "micro": None,              # None = micro par défaut de Windows
    "seuil_chant": 0.6,
    "cle_xeno_canto": "",       # facultative : plus d'enregistrements pour « Compléter les chants »
    "lieu": "",                 # position de la mangeoire : choisit les espèces locales (image et chants)
    "latitude": None,
    "longitude": None,
    "menage_jours": 60,
    "menage_go": 20,
    "demarrage_auto": False,
    "sources_recentes": [],
}

# Thème
FOND, CARTE, BORD = "#0f1419", "#17202a", "#263241"
TEXTE, DISCRET = "#e6edf3", "#8b98a5"
VERT, ROUGE, BLEU, AMBRE = "#3fb950", "#f85149", "#58a6ff", "#d29922"
COULEURS_ESPECES = ["#58a6ff", "#3fb950", "#d29922", "#f778ba", "#a371f7", "#79c0ff", "#ffa657", "#7ee787"]


def police(taille, gras=False):
    for nom in (["seguisb.ttf", "segoeuib.ttf"] if gras else ["segoeui.ttf"]):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            pass
    return ImageFont.load_default()


def surface_depuis_sensibilite(s):
    """Sensibilité 1..10 -> surface min. en mouvement (5 % .. 0,2 % de l'image), échelle log."""
    return 0.05 * (0.002 / 0.05) ** ((s - 1) / 9)


def libelle_source(source):
    return f"Webcam {source}" if str(source).isdigit() else str(source)


def affichage(espece):
    """« Inconnu » et « Pas un oiseau » sont notés en français dans le journal : traduits à l'affichage."""
    return _(espece) if espece in ("Inconnu", PAS_UN_OISEAU) else espece


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = {**DEFAUTS, **self._lire_config()}
        if self.cfg["langue"] not in LANGUES:
            self.cfg["langue"] = langues.langue_systeme()
        langues.regler(self.cfg["langue"])
        self.surveillance = None
        self.fil = None
        self.messages = queue.Queue()
        self.verrou = threading.Lock()
        self.derniere_image = None      # (image_bgr, etat)
        self.image_affichee = None
        self.vignettes = {}
        self.photo_visite = None
        self.reconnaisseur = self._nouveau_reconnaisseur()
        self.detecteur = DetecteurOiseaux()
        self.ecoute = None
        self.dernier_chant = None       # (espece, confiance, instant)
        self.chants_vus = set()
        self.f_tag, self.f_petit, self.f_vide = police(22, True), police(15), police(20)

        self._style()
        self._construire()
        self.charger_historique()
        threading.Thread(target=self._precharger_modele, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.quitter)
        self.root.after(30, self._boucle)
        if self.cfg["latitude"] is None:     # premier lancement : où est la mangeoire ?
            self.root.after(800, self.reglages)
        elif self.cfg["demarrage_auto"]:
            self.root.after(500, self.demarrer)

    # -------------------------------------------------------------- config
    def _lire_config(self):
        try:
            return json.loads(CONFIG.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _ecrire_config(self):
        try:
            CONFIG.write_text(json.dumps(self.cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    @property
    def dossier(self):
        return Path(self.cfg["dossier"])

    def _nouveau_reconnaisseur(self):
        return Reconnaisseur(MODELES, self.cfg["latitude"], self.cfg["longitude"], self.dossier / "corrections",
                             sur_message=lambda m: self.messages.put(("message", m)))

    # -------------------------------------------------------------- style
    def _style(self):
        r = self.root
        r.title("Becquée")
        r.configure(bg=FOND)
        r.geometry("1440x900")
        r.minsize(1100, 760)
        try:
            r.state("zoomed")      # plein écran au lancement
        except tk.TclError:
            pass
        icone = ICI / "becquee.ico"
        if icone.exists():
            try:
                r.iconbitmap(str(icone))
            except tk.TclError:
                pass
        s = ttk.Style(r)
        s.theme_use("clam")
        s.configure(".", background=FOND, foreground=TEXTE, font=("Segoe UI", 10),
                    bordercolor=BORD, lightcolor=CARTE, darkcolor=CARTE, troughcolor=BORD)
        s.configure("Carte.TFrame", background=CARTE)
        s.configure("TLabel", background=FOND, foreground=TEXTE)
        s.configure("Carte.TLabel", background=CARTE)
        s.configure("Discret.TLabel", background=CARTE, foreground=DISCRET)
        s.configure("Titre.TLabel", background=CARTE, foreground=DISCRET, font=("Segoe UI Semibold", 10))
        s.configure("TButton", background=CARTE, foreground=TEXTE, borderwidth=1, focusthickness=0,
                    padding=(14, 8), font=("Segoe UI Semibold", 10))
        s.map("TButton", background=[("active", BORD), ("disabled", CARTE)],
              foreground=[("disabled", DISCRET)])
        s.configure("Vert.TButton", background=VERT, foreground="#0b1f10", bordercolor=VERT)
        s.map("Vert.TButton", background=[("active", "#56d364")])
        s.configure("Rouge.TButton", background=ROUGE, foreground="white", bordercolor=ROUGE)
        s.map("Rouge.TButton", background=[("active", "#ff7b72")])
        s.configure("TCombobox", fieldbackground=CARTE, background=CARTE, foreground=TEXTE,
                    arrowcolor=TEXTE, padding=6)
        s.map("TCombobox", fieldbackground=[("readonly", CARTE)], foreground=[("readonly", TEXTE)])
        r.option_add("*TCombobox*Listbox.background", CARTE)
        r.option_add("*TCombobox*Listbox.foreground", TEXTE)
        r.option_add("*TCombobox*Listbox.selectBackground", BLEU)
        s.configure("Treeview", background=CARTE, fieldbackground=CARTE, foreground=TEXTE,
                    rowheight=52, borderwidth=0, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", background=CARTE, foreground=DISCRET, borderwidth=0,
                    font=("Segoe UI Semibold", 9))
        s.map("Treeview", background=[("selected", "#1f3a5f")])
        s.configure("TCheckbutton", background=CARTE, foreground=TEXTE)
        s.map("TCheckbutton", background=[("active", CARTE)])
        s.configure("Horizontal.TScale", background=CARTE, troughcolor=BORD)
        s.configure("Vertical.TScrollbar", background=CARTE, troughcolor=FOND, arrowcolor=DISCRET)
        s.configure("TNotebook", background=CARTE, borderwidth=0, tabmargins=0)
        s.configure("TNotebook.Tab", background=CARTE, foreground=DISCRET, padding=(14, 6),
                    font=("Segoe UI Semibold", 10), borderwidth=0)
        s.map("TNotebook.Tab", background=[("selected", BORD)], foreground=[("selected", TEXTE)])
        s.configure("TEntry", fieldbackground=CARTE, foreground=TEXTE, insertcolor=TEXTE)
        s.configure("TSpinbox", fieldbackground=CARTE, foreground=TEXTE, arrowcolor=TEXTE)
        r.option_add("*Menu.background", CARTE)
        r.option_add("*Menu.foreground", TEXTE)
        r.option_add("*Menu.activeBackground", BLEU)

    def _carte(self, parent, titre=None, **grid):
        cadre = ttk.Frame(parent, style="Carte.TFrame", padding=14)
        cadre.grid(**grid)
        if titre:
            ttk.Label(cadre, text=titre.upper(), style="Titre.TLabel").pack(anchor="w", pady=(0, 8))
        return cadre

    # -------------------------------------------------------------- interface
    def _construire(self):
        r = self.root
        r.columnconfigure(0, weight=1)
        r.rowconfigure(2, weight=1)

        # En-tête
        tete = tk.Frame(r, bg=FOND)
        tete.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))
        try:
            self.logo = ImageTk.PhotoImage(Image.open(ICI / "becquee.png").resize((48, 48), Image.LANCZOS))
            tk.Label(tete, image=self.logo, bg=FOND).pack(side="left", padx=(0, 12))
        except OSError:
            pass
        titres = tk.Frame(tete, bg=FOND)
        titres.pack(side="left")
        tk.Label(titres, text="Becquée", bg=FOND, fg=TEXTE, font=("Segoe UI Semibold", 20)).pack(anchor="w")
        tk.Label(titres, text=_("la mangeoire qui reconnaît ses visiteurs"), bg=FOND, fg=DISCRET,
                 font=("Segoe UI", 10)).pack(anchor="w")
        self.pastille = tk.Label(tete, text=_("●  En veille"), bg=CARTE, fg=DISCRET,
                                 font=("Segoe UI Semibold", 11), padx=14, pady=6)
        self.pastille.pack(side="right")
        self.lbl_modele = tk.Label(tete, text=_("Modèle : chargement…"), bg=FOND, fg=DISCRET, font=("Segoe UI", 10))
        self.lbl_modele.pack(side="right", padx=16)

        # Barre d'outils
        barre = tk.Frame(r, bg=FOND)
        barre.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 10))
        tk.Label(barre, text=_("Caméra"), bg=FOND, fg=DISCRET, font=("Segoe UI", 10)).pack(side="left")
        self.var_source = tk.StringVar(value=libelle_source(self.cfg["source"]))
        valeurs = [f"Webcam {i}" for i in range(3)] + self.cfg["sources_recentes"]
        self.cb_source = ttk.Combobox(barre, textvariable=self.var_source, values=valeurs, width=38)
        self.cb_source.pack(side="left", padx=(8, 12))
        self.btn_demarrer = ttk.Button(barre, text=_("▶  Démarrer"), style="Vert.TButton", command=self.basculer)
        self.btn_demarrer.pack(side="left")
        ttk.Button(barre, text=_("📷  Photo"), command=self.photo).pack(side="left", padx=(8, 0))
        ttk.Button(barre, text=_("📁  Dossier"), command=self.ouvrir_dossier).pack(side="left", padx=(8, 0))
        ttk.Button(barre, text=_("📊  Statistiques"), command=self.statistiques).pack(side="left", padx=(8, 0))
        ttk.Button(barre, text=_("🖼  Galerie"), command=self.galerie).pack(side="left", padx=(8, 0))
        ttk.Button(barre, text=_("⚙  Réglages"), command=self.reglages).pack(side="right")

        # Corps : vidéo + colonne droite
        corps = tk.Frame(r, bg=FOND)
        corps.grid(row=2, column=0, sticky="nsew", padx=20)
        corps.columnconfigure(0, weight=1)
        corps.rowconfigure(0, weight=1)

        cadre_video = tk.Frame(corps, bg="#000000", highlightthickness=1, highlightbackground=BORD)
        cadre_video.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.video = tk.Label(cadre_video, bg="#05080b")
        self.video.pack(fill="both", expand=True)
        self.video.bind("<Configure>", lambda e: self._afficher_vide() if self.surveillance is None else None)

        droite = tk.Frame(corps, bg=FOND, width=380)
        droite.grid(row=0, column=1, sticky="ns")
        droite.grid_propagate(False)
        droite.columnconfigure(0, weight=1)
        droite.rowconfigure(2, weight=1)

        # Dernière visite
        c = self._carte(droite, _("Dernière visite"), row=0, column=0, sticky="ew", pady=(0, 12))
        # cadre de taille fixe en pixels (un Label sans image compterait en lignes de texte)
        cadre_photo = tk.Frame(c, bg="#0b1016", width=350, height=170)
        cadre_photo.pack(fill="x")
        cadre_photo.pack_propagate(False)
        self.lbl_photo = tk.Label(cadre_photo, bg="#0b1016")
        self.lbl_photo.pack(fill="both", expand=True)
        self.lbl_espece = ttk.Label(c, text="—", style="Carte.TLabel", font=("Segoe UI Semibold", 16))
        self.lbl_espece.pack(anchor="w", pady=(10, 0))
        self.lbl_details = ttk.Label(c, text=_("Aucune visite pour l'instant"), style="Discret.TLabel", wraplength=340)
        self.lbl_details.pack(anchor="w")

        # Aujourd'hui
        c = self._carte(droite, _("Aujourd'hui"), row=1, column=0, sticky="ew", pady=(0, 12))
        ligne = ttk.Frame(c, style="Carte.TFrame")
        ligne.pack(fill="x")
        self.lbl_total = ttk.Label(ligne, text="0", style="Carte.TLabel", font=("Segoe UI Semibold", 28))
        self.lbl_total.pack(side="left")
        ttk.Label(ligne, text="  " + _("visites"), style="Discret.TLabel").pack(side="left", anchor="s", pady=(0, 8))
        self.stats = tk.Canvas(c, bg=CARTE, height=120, highlightthickness=0)
        self.stats.pack(fill="x", pady=(6, 0))

        # Historique : onglets Visites / Chants
        c = self._carte(droite, None, row=2, column=0, sticky="nsew")
        onglets = ttk.Notebook(c)
        onglets.pack(fill="both", expand=True)

        cadre_arbre = ttk.Frame(onglets, style="Carte.TFrame")
        onglets.add(cadre_arbre, text=_("Visites"))
        self.arbre = ttk.Treeview(cadre_arbre, columns=("quand", "espece", "conf"), show="tree headings",
                                  selectmode="browse")
        self.arbre.heading("#0", text="")
        self.arbre.column("#0", width=80, stretch=False)
        for col, titre, larg in (("quand", _("HEURE"), 62), ("espece", _("ESPÈCE"), 160), ("conf", _("CONF."), 48)):
            self.arbre.heading(col, text=titre, anchor="w")
            self.arbre.column(col, width=larg, anchor="w")
        defil = ttk.Scrollbar(cadre_arbre, orient="vertical", command=self.arbre.yview)
        self.arbre.configure(yscrollcommand=defil.set)
        self.arbre.pack(side="left", fill="both", expand=True)
        defil.pack(side="right", fill="y")
        self.arbre.bind("<<TreeviewSelect>>", self._selection)
        self.arbre.bind("<Double-1>", self._ouvrir_video)
        self.arbre.bind("<Button-3>", self._menu_correction)
        self.lignes = {}

        cadre_chants = ttk.Frame(onglets, style="Carte.TFrame")
        onglets.add(cadre_chants, text=_("Chants entendus"))
        ttk.Style(self.root).configure("Chants.Treeview", rowheight=26)
        self.arbre_chants = ttk.Treeview(cadre_chants, columns=("quand", "espece", "conf"), show="headings",
                                         style="Chants.Treeview")
        for col, titre, larg in (("quand", _("QUAND"), 80), ("espece", _("ESPÈCE"), 190), ("conf", _("CONF."), 50)):
            self.arbre_chants.heading(col, text=titre, anchor="w")
            self.arbre_chants.column(col, width=larg, anchor="w")
        defil2 = ttk.Scrollbar(cadre_chants, orient="vertical", command=self.arbre_chants.yview)
        self.arbre_chants.configure(yscrollcommand=defil2.set)
        self.arbre_chants.pack(side="left", fill="both", expand=True)
        defil2.pack(side="right", fill="y")
        ttk.Label(c, text=_("Clic droit sur une visite pour corriger l'espèce"), style="Discret.TLabel",
                  font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))

        # Pied : réglages rapides + état
        pied = ttk.Frame(r, style="Carte.TFrame", padding=(20, 10))
        pied.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(pied, text=_("Sensibilité"), style="Discret.TLabel").pack(side="left")
        self.var_sensi = tk.DoubleVar(value=self.cfg["sensibilite"])
        ttk.Scale(pied, from_=1, to=10, variable=self.var_sensi, length=160,
                  command=lambda v: self._maj_reglages()).pack(side="left", padx=(8, 4))
        self.lbl_sensi = ttk.Label(pied, width=4, style="Carte.TLabel")
        self.lbl_sensi.pack(side="left", padx=(0, 24))
        ttk.Label(pied, text=_("Seuil de reconnaissance"), style="Discret.TLabel").pack(side="left")
        self.var_seuil = tk.DoubleVar(value=self.cfg["seuil"] * 100)
        ttk.Scale(pied, from_=50, to=95, variable=self.var_seuil, length=160,
                  command=lambda v: self._maj_reglages()).pack(side="left", padx=(8, 4))
        self.lbl_seuil = ttk.Label(pied, width=5, style="Carte.TLabel")
        self.lbl_seuil.pack(side="left", padx=(0, 24))
        self.var_reco = tk.BooleanVar(value=self.cfg["reconnaissance"])
        ttk.Checkbutton(pied, text=_("Reconnaissance"), variable=self.var_reco,
                        command=self._maj_reglages).pack(side="left", padx=(0, 16))
        self.var_filtre = tk.BooleanVar(value=self.cfg["filtre_oiseaux"])
        ttk.Checkbutton(pied, text=_("Oiseaux seulement"), variable=self.var_filtre,
                        command=self._maj_reglages).pack(side="left", padx=(0, 16))
        self.var_ecoute = tk.BooleanVar(value=self.cfg["ecoute"])
        ttk.Checkbutton(pied, text=_("Écoute des chants"), variable=self.var_ecoute,
                        command=self._basculer_ecoute).pack(side="left")
        self.lbl_etat = ttk.Label(pied, text=_("Prêt"), style="Discret.TLabel", width=36, anchor="e")
        self.lbl_etat.pack(side="right")
        self._maj_reglages()

    # -------------------------------------------------------------- réglages
    def _maj_reglages(self):
        self.cfg["sensibilite"] = round(self.var_sensi.get(), 1)
        self.cfg["seuil"] = round(self.var_seuil.get() / 100, 2)
        self.cfg["reconnaissance"] = self.var_reco.get()
        self.cfg["filtre_oiseaux"] = self.var_filtre.get()
        self.lbl_sensi.configure(text=f"{self.cfg['sensibilite']:.0f}")
        self.lbl_seuil.configure(text=f"{self.cfg['seuil']:.0%}")
        if self.surveillance:
            self.surveillance.surface = surface_depuis_sensibilite(self.cfg["sensibilite"])
            self.surveillance.seuil = self.cfg["seuil"]
            self.surveillance.reconnaissance_active = self.cfg["reconnaissance"]
            self.surveillance.filtre_oiseaux = self.cfg["filtre_oiseaux"]

    def reglages(self):
        f = tk.Toplevel(self.root, bg=CARTE, padx=24, pady=20)
        f.title(_("Réglages — Becquée"))
        f.transient(self.root)
        f.resizable(False, False)
        lig = iter(range(100))

        def titre(texte):
            tk.Label(f, text=texte, bg=CARTE, fg=TEXTE, font=("Segoe UI Semibold", 11)).grid(
                row=next(lig), column=0, columnspan=3, sticky="w", pady=(14, 4))

        def champ(texte, var, largeur=10):
            r = next(lig)
            tk.Label(f, text=texte, bg=CARTE, fg=DISCRET).grid(row=r, column=0, sticky="w", pady=2)
            ttk.Entry(f, textvariable=var, width=largeur).grid(row=r, column=1, sticky="w", pady=2)

        titre(_("Langue"))
        r = next(lig)
        var_langue = tk.StringVar(value=LANGUES[langues.langue])
        ttk.Combobox(f, textvariable=var_langue, values=list(LANGUES.values()), state="readonly", width=20).grid(
            row=r, column=0, sticky="w")
        tk.Label(f, bg=CARTE, fg=DISCRET, font=("Segoe UI", 9), justify="left", wraplength=340,
                 text=_("Langue de l'interface et des noms d'espèces (redémarre Becquée).")).grid(
            row=r, column=1, columnspan=2, sticky="w", padx=(10, 0))

        titre(_("Position de la mangeoire"))
        var_lieu = tk.StringVar(value=self.cfg.get("lieu") or "")
        var_lat = tk.StringVar(value="" if self.cfg["latitude"] is None else str(self.cfg["latitude"]))
        var_lon = tk.StringVar(value="" if self.cfg["longitude"] is None else str(self.cfg["longitude"]))
        r = next(lig)
        champ_lieu = ttk.Entry(f, textvariable=var_lieu, width=52)
        champ_lieu.grid(row=r, column=0, columnspan=2, sticky="ew")
        lbl_lieu = tk.Label(f, bg=CARTE, fg=DISCRET, font=("Segoe UI", 9), justify="left", wraplength=520,
                            text=_("Ville, commune ou adresse — n'importe où dans le monde."))

        def chercher(evenement=None):
            texte = var_lieu.get().strip()
            if not texte:
                return
            lbl_lieu.configure(text=_("Recherche…"), fg=DISCRET)
            f.update_idletasks()
            try:
                trouve = chercher_lieu(texte)
            except Exception as e:
                trouve = None
                erreur = _("Recherche impossible ({erreur}) : saisissez latitude et longitude.", erreur=type(e).__name__)
            else:
                erreur = _("Lieu introuvable : précisez (ex. « Saint-Pierre, La Réunion »).")
            if trouve:
                var_lat.set(str(trouve[0]))
                var_lon.set(str(trouve[1]))
                lbl_lieu.configure(text=trouve[2], fg=VERT)
            else:
                lbl_lieu.configure(text=erreur, fg=AMBRE)
        champ_lieu.bind("<Return>", chercher)
        ttk.Button(f, text=_("Chercher"), command=chercher).grid(row=r, column=2, padx=(8, 0))
        lbl_lieu.grid(row=next(lig), column=0, columnspan=3, sticky="w", pady=(2, 4))
        champ(_("Latitude"), var_lat)
        champ(_("Longitude"), var_lon)
        tk.Label(f, justify="left", bg=CARTE, fg=DISCRET, font=("Segoe UI", 9), wraplength=520, text=_(
            "Becquée ne propose que les oiseaux observés autour de ce point (liste iNaturalist, "
            "mise à jour chaque mois) : la reconnaissance est bien plus fiable.")).grid(
            row=next(lig), column=0, columnspan=3, sticky="w", pady=(4, 0))

        titre(_("Enregistrement"))
        var_d = tk.StringVar(value=self.cfg["dossier"])
        r = next(lig)
        ttk.Entry(f, textvariable=var_d, width=52).grid(row=r, column=0, columnspan=2, sticky="ew")
        ttk.Button(f, text=_("Parcourir…"),
                   command=lambda: var_d.set(filedialog.askdirectory(initialdir=var_d.get()) or var_d.get())
                   ).grid(row=r, column=2, padx=(8, 0))
        var_garder = tk.BooleanVar(value=self.cfg["garder_sans_oiseau"])
        ttk.Checkbutton(f, text=_("Garder aussi les mouvements sans oiseau (déconseillé)"), variable=var_garder
                        ).grid(row=next(lig), column=0, columnspan=3, sticky="w", pady=(6, 0))
        var_auto = tk.BooleanVar(value=self.cfg["demarrage_auto"])
        ttk.Checkbutton(f, text=_("Démarrer la surveillance à l'ouverture"), variable=var_auto
                        ).grid(row=next(lig), column=0, columnspan=3, sticky="w")

        titre(_("Ménage automatique (0 = jamais)"))
        var_jours = tk.StringVar(value=str(self.cfg["menage_jours"]))
        var_go = tk.StringVar(value=str(self.cfg["menage_go"]))
        champ(_("Effacer les clips de plus de (jours)"), var_jours)
        champ(_("Taille maximale du dossier (Go)"), var_go)

        titre(_("Chants (BirdNET)"))
        try:
            import sounddevice as sd
            micros = [_("Micro par défaut de Windows")] + [f"{i} — {d['name']}" for i, d in enumerate(sd.query_devices())
                                                            if d["max_input_channels"] > 0]
        except Exception:
            micros = [_("Micro par défaut de Windows")]
        var_micro = tk.StringVar(value=next((m for m in micros if m.split(" — ")[0] == str(self.cfg["micro"])),
                                            micros[0]))
        r = next(lig)
        tk.Label(f, text=_("Micro"), bg=CARTE, fg=DISCRET).grid(row=r, column=0, sticky="w")
        ttk.Combobox(f, textvariable=var_micro, values=micros, state="readonly", width=46).grid(
            row=r, column=1, columnspan=2, sticky="w")
        var_sc = tk.StringVar(value=str(int(self.cfg["seuil_chant"] * 100)))
        champ(_("Seuil de confiance des chants (%)"), var_sc)
        var_xc = tk.StringVar(value=self.cfg.get("cle_xeno_canto", ""))
        champ(_("Clé API xeno-canto (facultative)"), var_xc, 34)
        r = next(lig)
        lbl_compl = tk.Label(f, bg=CARTE, fg=DISCRET, font=("Segoe UI", 9), justify="left", wraplength=360,
                             text=self._texte_complement())
        lbl_compl.grid(row=r, column=0, columnspan=2, sticky="w", pady=(6, 0))

        def completer():
            if self.cfg["latitude"] is None and not var_lat.get().strip():
                lbl_compl.configure(text=_("Réglez d'abord la position de la mangeoire."), fg=AMBRE)
                return
            self.cfg["cle_xeno_canto"] = var_xc.get().strip()
            lat, lon = nombre(var_lat, self.cfg["latitude"]), nombre(var_lon, self.cfg["longitude"])
            lbl_compl.configure(text=_("Apprentissage en cours (plusieurs minutes)… voir la barre d'état."), fg=DISCRET)
            threading.Thread(target=self._completer_chants, args=(lat, lon, lbl_compl), daemon=True).start()
        ttk.Button(f, text=_("Compléter les chants"), command=completer).grid(row=r, column=2, padx=(8, 0), pady=(6, 0))
        tk.Label(f, justify="left", bg=CARTE, fg=DISCRET, font=("Segoe UI", 9), text=_(
            "Smartphone : appli « IP Webcam » (Android), adresse du type http://192.168.1.20:8080/video.\n"
            "Caméra sur Internet (nid, mangeoire) : collez l'adresse de la page YouTube ou du flux,\n"
            "et réglez la position sur le lieu de la caméra. Le micro du PC n'est pas utilisé pour ses visites.\n"
            "L'écoute utilise le micro du PC (ou de la webcam USB).")).grid(
            row=next(lig), column=0, columnspan=3, sticky="w", pady=(12, 0))

        def nombre(var, defaut):
            try:
                return float(var.get().replace(",", "."))
            except ValueError:
                return defaut

        def valider():
            avant = (self.cfg["latitude"], self.cfg["longitude"], self.cfg["dossier"])
            self.cfg["lieu"] = var_lieu.get().strip()
            self.cfg["dossier"] = var_d.get()
            self.cfg["garder_sans_oiseau"] = var_garder.get()
            self.cfg["demarrage_auto"] = var_auto.get()
            self.cfg["menage_jours"] = nombre(var_jours, 60)
            self.cfg["menage_go"] = nombre(var_go, 20)
            m = var_micro.get().split(" — ")[0]
            self.cfg["micro"] = int(m) if m.isdigit() else None
            self.cfg["latitude"] = nombre(var_lat, None) if var_lat.get().strip() else None
            self.cfg["longitude"] = nombre(var_lon, None) if var_lon.get().strip() else None
            self.cfg["seuil_chant"] = min(0.99, max(0.1, nombre(var_sc, 60) / 100))
            self.cfg["cle_xeno_canto"] = var_xc.get().strip()
            nouvelle = next(code for code, nom in LANGUES.items() if nom == var_langue.get())
            if nouvelle != self.cfg["langue"]:      # nouvelle langue : on redémarre l'application
                self.cfg["langue"] = nouvelle
                f.destroy()
                self.redemarrer()
                return
            self._ecrire_config()
            self.charger_historique()
            if (self.cfg["latitude"], self.cfg["longitude"], self.cfg["dossier"]) != avant:
                # nouvelles espèces locales / nouvelles corrections : nouveau reconnaisseur
                threading.Thread(target=self._precharger_modele, args=(self._nouveau_reconnaisseur(),),
                                 daemon=True).start()
            if self.ecoute:      # relance l'écoute avec les nouveaux réglages
                self._arreter_ecoute()
                self._demarrer_ecoute()
            f.destroy()
        ttk.Button(f, text=_("Enregistrer"), style="Vert.TButton", command=valider).grid(
            row=next(lig), column=2, sticky="e", pady=(20, 0))

    # -------------------------------------------------------------- écoute des chants
    def _texte_complement(self):
        f = MODELES / "chants_complement.npz"
        texte = _("Espèces locales absentes de BirdNET (endémiques…) : Becquée apprend leurs chants "
                  "(iNaturalist, xeno-canto, sons gardés lors des visites reconnues à l'image).")
        if f.exists():
            try:
                import numpy as np
                z = np.load(f)
                texte += "\n" + _("Déjà appris : {n} espèces (le {date}).", n=len(z["sci"]) - 1, date=str(z["date"])[:10])
            except Exception:
                pass
        return texte

    def _completer_chants(self, lat, lon, etiquette):
        import chants_complement
        dire = lambda m: self.messages.put(("message", m))
        try:
            resume = chants_complement.completer(MODELES, lat, lon, self.cfg.get("cle_xeno_canto", ""),
                                                 self.dossier / "chants_perso", sur_message=dire)
            apprises = [k for k, v in resume.items() if not k.startswith("_") and v.get("enregistrements")]
            texte = _("Appris : {n} espèces. Seuil {seuil} (fausses alertes {fa}).", n=len(apprises),
                      seuil=f"{resume.get('_seuil', 0):.0%}", fa=f"{resume.get('_fausses_alertes', 0):.1%}")
        except Exception as e:
            texte = _("Apprentissage impossible ({erreur})", erreur=f"{type(e).__name__} : {e}")
        dire(texte)

        def fin():
            try:
                etiquette.configure(text=texte, fg=VERT)
            except tk.TclError:
                pass        # fenêtre Réglages fermée entre-temps
            if self.ecoute:
                self._arreter_ecoute()
                self._demarrer_ecoute()
        self.root.after(0, fin)

    def _demarrer_ecoute(self):
        if self.ecoute or not self.cfg["ecoute"]:
            return
        if not (MODELES / "birdnet.onnx").exists():
            self.lbl_etat.configure(text=_("Modèle BirdNET en cours de téléchargement…"))
            return
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.ecoute = Ecoute(MODELES, self.dossier, seuil=self.cfg["seuil_chant"],
                             latitude=self.cfg["latitude"], longitude=self.cfg["longitude"], micro=self.cfg["micro"],
                             sur_chant=lambda e, c: self.messages.put(("chant", (e, c, datetime.now()))),
                             sur_message=lambda m: self.messages.put(("message", m)))
        self.ecoute.demarrer()
        if self.surveillance:
            self.surveillance.ecoute = self.ecoute

    def _arreter_ecoute(self):
        if self.ecoute:
            self.ecoute.arreter()
            self.ecoute = None
            if self.surveillance:
                self.surveillance.ecoute = None

    def _basculer_ecoute(self):
        self.cfg["ecoute"] = self.var_ecoute.get()
        if self.cfg["ecoute"] and self.surveillance:
            self._demarrer_ecoute()
        elif not self.cfg["ecoute"]:
            self._arreter_ecoute()

    def _ajouter_chant(self, espece, conf, instant, en_tete=True):
        cle = (espece, instant.strftime("%Y-%m-%d %H:%M"))
        if cle in self.chants_vus:          # une ligne par espèce et par minute
            return
        self.chants_vus.add(cle)
        quand = instant.strftime("%H:%M") if instant.date() == datetime.now().date() else instant.strftime("%d/%m %H:%M")
        self.arbre_chants.insert("", 0 if en_tete else "end", values=(quand, espece, f"{conf:.0%}"))

    # -------------------------------------------------------------- surveillance
    def basculer(self):
        self.arreter() if self.surveillance else self.demarrer()

    def demarrer(self):
        texte = self.var_source.get().strip()
        source = texte.split()[-1] if texte.startswith("Webcam ") else texte
        if not source:
            return
        self.cfg["source"] = source
        if not source.isdigit() and source not in self.cfg["sources_recentes"]:
            self.cfg["sources_recentes"] = ([source] + self.cfg["sources_recentes"])[:5]
            self.cb_source.configure(values=[f"Webcam {i}" for i in range(3)] + self.cfg["sources_recentes"])
        self._ecrire_config()
        self.surveillance = Surveillance(
            source, self.dossier, seuil=self.cfg["seuil"],
            surface=surface_depuis_sensibilite(self.cfg["sensibilite"]),
            reconnaissance=self.cfg["reconnaissance"], reconnaisseur=self.reconnaisseur, temps_reel=True,
            filtre_oiseaux=self.cfg["filtre_oiseaux"], garder_sans_oiseau=self.cfg["garder_sans_oiseau"],
            detecteur_oiseaux=self.detecteur, menage_jours=self.cfg["menage_jours"], menage_go=self.cfg["menage_go"],
            sur_image=self._sur_image,
            sur_visite=lambda l: self.messages.put(("visite", l)),
            sur_message=lambda m: self.messages.put(("message", m)))
        self._demarrer_ecoute()
        self.surveillance.ecoute = self.ecoute
        s = self.surveillance
        self.fil = threading.Thread(target=lambda: self.messages.put(("fin", s.executer())), daemon=True)
        self.fil.start()
        self.btn_demarrer.configure(text=_("■  Arrêter"), style="Rouge.TButton")
        self._pastille(_("●  Connexion…"), AMBRE)

    def arreter(self):
        if self.surveillance:
            self.surveillance.arreter()
        self.btn_demarrer.configure(state="disabled")

    def _sur_image(self, image, etat):
        with self.verrou:
            self.derniere_image = (image, etat)

    def _pastille(self, texte, couleur):
        self.pastille.configure(text=texte, fg=couleur)

    # -------------------------------------------------------------- boucle UI
    def _boucle(self):
        while not self.messages.empty():
            genre, contenu = self.messages.get()
            if genre == "message":
                self.lbl_etat.configure(text=contenu)
            elif genre == "visite":
                self._ajouter_visite(contenu, en_tete=True)
                self._afficher_visite(contenu)
                self._maj_stats()
            elif genre == "chant":
                espece, conf, instant = contenu
                self.dernier_chant = (espece, conf, time.time())
                self._ajouter_chant(espece, conf, instant)
            elif genre == "fin":
                if not contenu:
                    messagebox.showerror(_("Caméra"), self.lbl_etat.cget("text"))
                self._arreter_ecoute()
                self.surveillance, self.derniere_image = None, None
                self.btn_demarrer.configure(text=_("▶  Démarrer"), style="Vert.TButton", state="normal")
                self._pastille(_("●  En veille"), DISCRET)
                self._afficher_vide()

        # micro muet (coupé au clavier ou niveau à 0 dans Windows) : on le signale
        if self.ecoute and self.ecoute.fil and time.time() - getattr(self, "_controle_micro", 0) > 5:
            self._controle_micro = time.time()
            if not hasattr(self.ecoute, "_debut"):
                self.ecoute._debut = time.time()
            elif time.time() - self.ecoute._debut > 15 and self.ecoute.niveau < 2e-4:
                self.lbl_etat.configure(text=_("Micro muet : vérifiez Paramètres › Son › Entrée"), foreground=AMBRE)
            else:
                self.lbl_etat.configure(foreground=DISCRET)

        with self.verrou:
            donnees, self.derniere_image = self.derniere_image, None
        if donnees and self.surveillance:
            image, etat = donnees
            self._afficher_image(image, etat)
            if etat["enregistrement"]:
                self._pastille(_("●  Visite en cours"), ROUGE)
            else:
                self._pastille(_("●  Surveillance"), VERT)
        self.root.after(30, self._boucle)

    def _afficher_image(self, image, etat):
        lw, lh = max(self.video.winfo_width(), 320), max(self.video.winfo_height(), 240)
        h, w = image.shape[:2]
        e = min(lw / w, lh / h)
        nw, nh = int(w * e), int(h * e)
        img = Image.fromarray(cv2.cvtColor(cv2.resize(image, (nw, nh)), cv2.COLOR_BGR2RGB)).convert("RGBA")
        calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(calque)
        if etat["boite"] is not None:
            x, y, bw, bh = (int(v * e) for v in etat["boite"])
            d.rounded_rectangle([x, y, x + bw, y + bh], radius=8, outline=(63, 185, 80, 140), width=2)
        for b in etat.get("oiseaux", []):       # oiseaux détectés : cadre ambré
            x, y, bw, bh = (int(v * e) for v in b)
            d.rounded_rectangle([x, y, x + bw, y + bh], radius=10, outline=(255, 176, 32, 255), width=4)
        if self.dernier_chant and time.time() - self.dernier_chant[2] < 10:
            t = _("Chant : {espece}  {conf}", espece=self.dernier_chant[0], conf=f"{self.dernier_chant[1]:.0%}")
            tw = d.textlength(t, font=self.f_petit)
            d.rounded_rectangle([nw - tw - 66, 52, nw - 16, 86], radius=16, fill=(88, 166, 255, 220))
            # petite note de musique dessinée (la police n'a pas le caractère ♪)
            nx, ny = nw - tw - 52, 62
            d.ellipse([nx, ny + 10, nx + 8, ny + 16], fill="white")
            d.line([nx + 7, ny + 13, nx + 7, ny], fill="white", width=2)
            d.line([nx + 7, ny, nx + 13, ny + 4], fill="white", width=2)
            d.text((nw - tw - 31, 57), t, font=self.f_petit, fill="white")
        if etat["enregistrement"]:
            d.rounded_rectangle([16, 16, 150, 52], radius=18, fill=(248, 81, 73, 230))
            d.ellipse([28, 28, 40, 40], fill="white")
            d.text((50, 22), f"REC {int(etat['duree']) // 60:02d}:{int(etat['duree']) % 60:02d}",
                   font=self.f_petit, fill="white")
        if etat["etiquette"]:
            t = etat["etiquette"]
            tw = d.textlength(t, font=self.f_tag)
            d.rounded_rectangle([16, nh - 70, 16 + tw + 36, nh - 18], radius=14, fill=(15, 20, 25, 210))
            d.text((34, nh - 64), t, font=self.f_tag, fill=(230, 237, 243, 255))
        d.text((nw - 90, 20), _("{fps} i/s", fps=f"{etat['fps']:.0f}"), font=self.f_petit, fill=(200, 210, 220, 200))
        img = Image.alpha_composite(img, calque).convert("RGB")
        self.image_affichee = ImageTk.PhotoImage(img)
        self.video.configure(image=self.image_affichee)

    def _afficher_vide(self):
        lw, lh = max(self.video.winfo_width(), 320), max(self.video.winfo_height(), 240)
        img = Image.new("RGB", (lw, lh), (5, 8, 11))
        d = ImageDraw.Draw(img)
        try:
            logo = Image.open(ICI / "becquee.png").convert("RGBA").resize((128, 128), Image.LANCZOS)
            img.paste(logo, ((lw - 128) // 2, lh // 2 - 150), logo)
        except OSError:
            pass
        t = _("Cliquez sur « Démarrer » pour lancer la surveillance")
        d.text(((lw - d.textlength(t, font=self.f_vide)) / 2, lh / 2 + 10), t, font=self.f_vide,
               fill=(139, 152, 165))
        self.image_affichee = ImageTk.PhotoImage(img)
        self.video.configure(image=self.image_affichee)

    # -------------------------------------------------------------- visites
    def charger_historique(self):
        self.arbre.delete(*self.arbre.get_children())
        self.lignes.clear()
        self.vignettes.clear()
        lignes = lire_journal(self.dossier)[-300:]
        for l in lignes:
            self._ajouter_visite(l, en_tete=True)
        if lignes:
            self._afficher_visite(lignes[-1])
        self._maj_stats()
        self.arbre_chants.delete(*self.arbre_chants.get_children())
        self.chants_vus.clear()
        for l in lire_journal(self.dossier, "chants.csv")[-300:]:
            try:
                instant = datetime.strptime(f"{l['date']} {l['heure']}", "%Y-%m-%d %H:%M:%S")
                self._ajouter_chant(l["espece"], float(l["confiance"]), instant)
            except (KeyError, ValueError):
                pass

    def _vignette(self, ligne, taille):
        if not ligne.get("photo"):
            return None
        try:
            img = Image.open(self.dossier / ligne["photo"])
            img.thumbnail(taille)
            return ImageTk.PhotoImage(img)
        except OSError:
            return None

    def _ajouter_visite(self, ligne, en_tete):
        aujourd_hui = datetime.now().strftime("%Y-%m-%d")
        quand = ligne["heure"][:5] if ligne["date"] == aujourd_hui else f"{ligne['date'][8:]}/{ligne['date'][5:7]} {ligne['heure'][:5]}"
        vignette = self._vignette(ligne, (72, 48))
        conf = "✔" if ligne.get("corrige") else f"{float(ligne['confiance']):.0%}"
        iid = self.arbre.insert("", 0 if en_tete else "end", text="", image=vignette or "",
                                values=(quand, affichage(ligne["espece"]), conf))
        if vignette:
            self.vignettes[iid] = vignette
        self.lignes[iid] = ligne

    def _afficher_visite(self, ligne):
        self.photo_visite = self._vignette(ligne, (350, 170))
        self.lbl_photo.configure(image=self.photo_visite or "")
        self.lbl_espece.configure(text=affichage(ligne["espece"]),
                                  foreground=DISCRET if ligne["espece"] == "Inconnu" else TEXTE)
        source = {"image": _("par l'image"), "chant": _("par le chant"), "image+chant": _("image + chant"),
                  "manuel": _("corrigé à la main")}.get(ligne.get("source") or "", "")
        quand = _("{jour}/{mois} à {heure}", jour=ligne["date"][8:], mois=ligne["date"][5:7], heure=ligne["heure"][:5])
        details = (f"{quand}  ·  {float(ligne['confiance']):.0%}{'  ' + source if source else ''}"
                   f"  ·  {ligne['duree_s']} s")
        if ligne.get("chants"):
            details += "\n" + _("Chants entendus : {liste}", liste=ligne["chants"])
        self.lbl_details.configure(text=details)

    def _menu_correction(self, evenement):
        iid = self.arbre.identify_row(evenement.y)
        if not iid:
            return
        self.arbre.selection_set(iid)
        ligne = self.lignes[iid]
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=_("Corriger « {espece} » en :", espece=affichage(ligne["espece"])), state="disabled")
        r = self.reconnaisseur
        # propositions : espèces déjà vues ici, les 3 suivantes du modèle, chants entendus, espèces apprises,
        # puis les plus courantes du coin
        vues = [e for e, _ in Counter(l["espece"] for l in self.lignes.values()).most_common(10)]
        entendues = [e for e, _ in Counter(v[0] for v in self.chants_vus).most_common(8)]
        apprises = r.noms[len(r.especes):]
        courantes = [e["nom"] for e in r.especes[:15]]
        propositions = [e for e in dict.fromkeys(vues + entendues + apprises + courantes)
                        if e not in ("Inconnu", PAS_UN_OISEAU, ligne["espece"])][:24]
        for espece in propositions:
            menu.add_command(label=espece, command=lambda e=espece: self._corriger(iid, e))
        menu.add_separator()
        menu.add_command(label=_("Autre espèce…"), command=lambda: self._corriger(
            iid, simpledialog.askstring(_("Corriger"), _("Nom de l'espèce (commun ou scientifique) :"),
                                        parent=self.root)))
        menu.add_command(label=_(PAS_UN_OISEAU), command=lambda: self._corriger(iid, PAS_UN_OISEAU))
        menu.tk_popup(evenement.x_root, evenement.y_root)

    def _nom_connu(self, saisie):
        """« bulbul orphee » ou « Pycnonotus jocosus » -> « Bulbul orphée » si l'espèce est connue."""
        cle = cle_espece(saisie)
        if cle in (cle_espece(PAS_UN_OISEAU), cle_espece(_(PAS_UN_OISEAU))):
            return PAS_UN_OISEAU
        r = self.reconnaisseur
        for e in r.especes:
            if cle in (cle_espece(e["nom"]), cle_espece(e["sci"]), cle_espece(e["en"])):
                return e["nom"]
        return next((n for n in r.noms if cle_espece(n) == cle), saisie)

    def _corriger(self, iid, espece):
        if not espece or not espece.strip():
            return
        espece = self._nom_connu(espece.strip())
        ligne = corriger_visite(self.dossier, self.lignes[iid]["video"], espece)
        if ligne:
            self.lignes[iid] = ligne
            self.arbre.item(iid, values=(self.arbre.item(iid, "values")[0], affichage(ligne["espece"]), "✔"))
            self._afficher_visite(ligne)
            self._maj_stats()
            self.lbl_etat.configure(text=_("Corrigé : {espece} — Becquée apprend de cette photo…",
                                           espece=affichage(espece)))
            self._apprendre()

    def _maj_stats(self):
        aujourd_hui = datetime.now().strftime("%Y-%m-%d")
        comptes = Counter(affichage(l["espece"]) for l in self.lignes.values() if l["date"] == aujourd_hui)
        self.lbl_total.configure(text=str(sum(comptes.values())))
        c = self.stats
        c.delete("all")
        largeur = max(c.winfo_width(), 340)
        if not comptes:
            c.configure(height=30)
            c.create_text(0, 14, anchor="w", text=_("Pas encore de visite aujourd'hui"), fill=DISCRET,
                          font=("Segoe UI", 10))
            return
        top = comptes.most_common(5)
        c.configure(height=26 * len(top))
        maxi = top[0][1]
        from tkinter import font as tkfont
        f = tkfont.Font(family="Segoe UI", size=10)
        noms = [e if len(e) <= 22 else e[:21] + "…" for e, _ in top]
        x0 = max(f.measure(n) for n in noms) + 12       # la barre commence après le nom le plus long
        for i, ((espece, n), nom) in enumerate(zip(top, noms)):
            y = i * 26 + 4
            barre = max(4, (largeur - x0 - 40) * n / maxi)
            c.create_text(0, y + 9, anchor="w", text=nom, fill=TEXTE, font=f)
            c.create_rectangle(x0, y + 3, x0 + barre, y + 15,
                               fill=COULEURS_ESPECES[i % len(COULEURS_ESPECES)], width=0)
            c.create_text(x0 + barre + 8, y + 9, anchor="w", text=str(n), fill=DISCRET, font=("Segoe UI", 9))

    def _selection(self, _):
        sel = self.arbre.selection()
        if sel:
            self._afficher_visite(self.lignes[sel[0]])

    def _ouvrir_video(self, _):
        sel = self.arbre.selection()
        if sel:
            chemin = self.dossier / self.lignes[sel[0]]["video"]
            if chemin.exists():
                os.startfile(chemin)

    # -------------------------------------------------------------- actions
    def photo(self):
        with self.verrou:
            donnees = self.derniere_image
        image = donnees[0] if donnees else None
        if image is None:
            self.lbl_etat.configure(text=_("Démarrez la surveillance pour prendre une photo"))
            return
        dossier = self.dossier / "photos"
        dossier.mkdir(parents=True, exist_ok=True)
        chemin = dossier / f"{datetime.now():%Y-%m-%d_%H-%M-%S}.jpg"
        Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).save(chemin, quality=92)
        self.lbl_etat.configure(text=_("Photo enregistrée : {nom}", nom=chemin.name))

    def ouvrir_dossier(self):
        self.dossier.mkdir(parents=True, exist_ok=True)
        os.startfile(self.dossier)

    # -------------------------------------------------------------- statistiques
    def statistiques(self):
        f = tk.Toplevel(self.root, bg=FOND, padx=20, pady=16)
        f.title(_("Statistiques — Becquée"))
        f.transient(self.root)
        f.geometry("1000x760")
        visites = [l for l in lire_journal(self.dossier) if l["espece"] != PAS_UN_OISEAU]
        var_periode = tk.StringVar(value="30")

        haut = tk.Frame(f, bg=FOND)
        haut.pack(fill="x")
        for valeur, texte in (("7", _("7 jours")), ("30", _("30 jours")), ("0", _("Tout"))):
            tk.Radiobutton(haut, text=texte, value=valeur, variable=var_periode, indicatoron=False,
                           bg=CARTE, fg=TEXTE, selectcolor=BORD, activebackground=BORD, activeforeground=TEXTE,
                           font=("Segoe UI Semibold", 10), padx=14, pady=5, bd=0,
                           command=lambda: dessiner()).pack(side="left", padx=(0, 6))
        chiffres = tk.Frame(f, bg=FOND)
        chiffres.pack(fill="x", pady=(14, 10))
        corps = tk.Frame(f, bg=FOND)
        corps.pack(fill="both", expand=True)
        corps.columnconfigure(0, weight=1)
        corps.columnconfigure(1, weight=1)
        corps.rowconfigure(1, weight=1)

        def carte(titre, **grid):
            c = self._carte(corps, titre, **grid)
            toile = tk.Canvas(c, bg=CARTE, highlightthickness=0, height=200)
            toile.pack(fill="both", expand=True)
            return toile
        t_especes = carte(_("Visites par espèce"), row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))
        t_heures = carte(_("Visites par heure"), row=0, column=1, sticky="nsew", pady=(0, 12))
        t_jours = carte(_("Visites par jour"), row=1, column=1, sticky="nsew")

        def dessiner():
            jours = int(var_periode.get())
            debut = (datetime.now() - timedelta(days=jours - 1)).strftime("%Y-%m-%d") if jours else ""
            choix = [l for l in visites if l["date"] >= debut]
            nommees = [l for l in choix if l["espece"] != "Inconnu"]
            especes = Counter(l["espece"] for l in nommees)

            for w in chiffres.winfo_children():
                w.destroy()
            for valeur, texte in ((len(choix), _("visites")), (len(especes), _("espèces")),
                                  (especes.most_common(1)[0][0] if especes else "—", _("espèce la plus fréquente"))):
                c = tk.Frame(chiffres, bg=CARTE, padx=16, pady=10)
                c.pack(side="left", padx=(0, 12))
                tk.Label(c, text=str(valeur), bg=CARTE, fg=TEXTE, font=("Segoe UI Semibold", 22)).pack(anchor="w")
                tk.Label(c, text=texte, bg=CARTE, fg=DISCRET, font=("Segoe UI", 10)).pack(anchor="w")

            f.update_idletasks()
            # visites par espèce : barres horizontales, les plus fréquentes en haut
            t = t_especes
            t.delete("all")
            larg, haut_t = t.winfo_width(), t.winfo_height()
            top = especes.most_common(max(1, (haut_t - 4) // 24))
            if not top:
                t.create_text(0, 14, anchor="w", text=_("Aucune visite sur cette période"), fill=DISCRET,
                              font=("Segoe UI", 10))
            else:
                from tkinter import font as tkfont
                fnt = tkfont.Font(family="Segoe UI", size=10)
                noms = [e if len(e) <= 24 else e[:23] + "…" for e, _ in top]
                x0 = max(fnt.measure(n) for n in noms) + 12
                for i, ((espece, n), nom) in enumerate(zip(top, noms)):
                    y = i * 24 + 4
                    barre = max(4, (larg - x0 - 44) * n / top[0][1])
                    t.create_text(0, y + 9, anchor="w", text=nom, fill=TEXTE, font=fnt)
                    t.create_rectangle(x0, y + 3, x0 + barre, y + 15,
                                       fill=COULEURS_ESPECES[i % len(COULEURS_ESPECES)], width=0)
                    t.create_text(x0 + barre + 8, y + 9, anchor="w", text=str(n), fill=DISCRET,
                                  font=("Segoe UI", 9))

            def colonnes(toile, valeurs, etiquettes, pas_etiquette):
                toile.delete("all")
                larg, haut_t = toile.winfo_width(), toile.winfo_height()
                maxi = max(valeurs) or 1
                pas = larg / len(valeurs)
                for i, (v, e) in enumerate(zip(valeurs, etiquettes)):
                    h = (haut_t - 30) * v / maxi
                    x = i * pas
                    if v:
                        toile.create_rectangle(x + pas * 0.15, haut_t - 20 - h, x + pas * 0.85, haut_t - 20,
                                               fill=BLEU, width=0)
                    if i % pas_etiquette == 0:
                        toile.create_text(x + pas / 2, haut_t - 8, text=e, fill=DISCRET, font=("Segoe UI", 8))
                toile.create_text(larg - 2, 2, anchor="ne", text=f"max {maxi}", fill=DISCRET, font=("Segoe UI", 8))

            heures = Counter(int(l["heure"][:2]) for l in choix)
            colonnes(t_heures, [heures[h] for h in range(24)], [f"{h}h" for h in range(24)], 3)
            nb_jours = jours or max(1, (datetime.now() - datetime.strptime(
                min((l["date"] for l in choix), default=datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")).days + 1)
            dates = [(datetime.now() - timedelta(days=nb_jours - 1 - i)) for i in range(nb_jours)]
            par_jour = Counter(l["date"] for l in choix)
            colonnes(t_jours, [par_jour[d.strftime("%Y-%m-%d")] for d in dates],
                     [d.strftime("%d/%m") for d in dates], max(1, nb_jours // 8))

        f.bind("<Configure>", lambda e: dessiner() if e.widget is f else None)
        f.after(50, dessiner)

    # -------------------------------------------------------------- galerie
    def galerie(self):
        if not (self.dossier / "galerie" / "galerie.json").exists():
            construire_galerie(self.dossier)
        index = lire_galerie(self.dossier)
        nb_visites = Counter(l["espece"] for l in lire_journal(self.dossier))
        f = tk.Toplevel(self.root, bg=FOND, padx=16, pady=16)
        f.title(_("Galerie — Becquée"))
        f.transient(self.root)
        f.geometry("1200x760")
        if not index:
            tk.Label(f, text=_("Aucune photo pour l'instant"), bg=FOND, fg=DISCRET,
                     font=("Segoe UI", 12)).pack(pady=40)
            return
        toile = tk.Canvas(f, bg=FOND, highlightthickness=0)
        defil = ttk.Scrollbar(f, orient="vertical", command=toile.yview)
        toile.configure(yscrollcommand=defil.set)
        defil.pack(side="right", fill="y")
        toile.pack(side="left", fill="both", expand=True)
        grille = tk.Frame(toile, bg=FOND)
        toile.create_window(0, 0, anchor="nw", window=grille)
        grille.bind("<Configure>", lambda e: toile.configure(scrollregion=toile.bbox("all")))
        f.bind("<MouseWheel>", lambda e: toile.yview_scroll(-e.delta // 120, "units"))
        f.images = []
        especes = sorted(index, key=lambda e: (-nb_visites[e], e))
        for i, espece in enumerate(especes):
            e = index[espece]
            chemin = self.dossier / e["photo"]
            c = tk.Frame(grille, bg=CARTE, padx=8, pady=8, cursor="hand2")
            c.grid(row=i // 4, column=i % 4, padx=(0, 12), pady=(0, 12), sticky="n")
            try:
                img = Image.open(chemin)
                img.thumbnail((250, 170))
                f.images.append(ImageTk.PhotoImage(img))
                photo = tk.Label(c, image=f.images[-1], bg="#0b1016", width=250, height=170)
            except OSError:
                photo = tk.Label(c, bg="#0b1016", width=35, height=10)
            photo.pack()
            tk.Label(c, text=espece, bg=CARTE, fg=TEXTE, font=("Segoe UI Semibold", 11),
                     wraplength=250, justify="left").pack(anchor="w", pady=(6, 0))
            quand = _("{jour}/{mois} à {heure}", jour=e["date"][8:], mois=e["date"][5:7], heure=e["heure"][:5])
            tk.Label(c, text=f"{float(e['confiance']):.0%}  ·  {quand}  ·  {nb_visites[espece]} " + _("visites"),
                     bg=CARTE, fg=DISCRET, font=("Segoe UI", 9)).pack(anchor="w")
            for w in (c, *c.winfo_children()):
                w.bind("<Button-1>", lambda ev, p=chemin: os.startfile(p) if p.exists() else None)

    def _precharger_modele(self, reconnaisseur=None):
        """Charge les modèles ; un nouveau reconnaisseur (position ou dossier changés) remplace
        l'ancien seulement une fois prêt, sans interrompre la surveillance."""
        r = reconnaisseur or self.reconnaisseur
        self.root.after(0, lambda: self.lbl_modele.configure(text=_("Chargement des modèles…"), fg=DISCRET))
        try:
            Ecoute.telecharger(MODELES)          # étiquettes BirdNET : noms français, liste de secours
            r.charger()
            self.detecteur.charger()
            if reconnaisseur is not None:
                self.reconnaisseur = reconnaisseur
                if self.surveillance:
                    self.surveillance.reconnaisseur = reconnaisseur
            texte, couleur = self._texte_modele(), VERT
        except Exception as e:  # pas de réseau au premier lancement, etc.
            texte, couleur = _("Modèle indisponible ({erreur})", erreur=type(e).__name__), ROUGE
        self.root.after(0, lambda: self.lbl_modele.configure(text=texte, fg=couleur))

    def _texte_modele(self):
        r = self.reconnaisseur
        texte = _("Modèles prêts · {n} espèces locales", n=len(r.especes))
        if r.nb_exemples:
            texte += _(" · photos apprises : {n}", n=r.nb_exemples)
        return texte

    def _apprendre(self):
        """Ajoute les nouvelles corrections à la mémoire du reconnaisseur (en arrière-plan)."""
        def tache():
            try:
                n, e = self.reconnaisseur.apprendre()
                texte = _("Appris — photos corrigées : {n}, espèces : {e}", n=n, e=e)
            except Exception as ex:
                texte = _("Apprentissage impossible ({erreur})", erreur=type(ex).__name__)
            self.root.after(0, lambda: (self.lbl_etat.configure(text=texte),
                                        self.lbl_modele.configure(text=self._texte_modele(), fg=VERT)))
        threading.Thread(target=tache, daemon=True).start()

    def redemarrer(self):
        """Ferme proprement (la visite en cours est terminée) puis relance Becquée (changement de langue)."""
        import subprocess
        self.quitter()
        subprocess.Popen([sys.executable] + sys.argv, cwd=str(ICI))

    def quitter(self):
        self._ecrire_config()
        self._arreter_ecoute()
        if self.surveillance:
            self.surveillance.arreter()
            if self.fil:
                self.root.title(_("Becquée — enregistrement de la visite en cours…"))
                self.fil.join(timeout=15)      # laisse le temps de terminer le clip en cours
        self.root.destroy()


def main():
    try:   # netteté sur les écrans à haute résolution
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
