"""Dessine le schéma de fonctionnement de Becquée (docs/schema_fr.png, docs/schema_en.png).
python docs/schema.py"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
FOND, CARTE, BORD, TEXTE, DISCRET = "#0f1419", "#17202a", "#263241", "#e6edf3", "#8b98a5"
VERT, AMBRE, BLEU, ROUGE, VIOLET = "#3fb950", "#d29922", "#58a6ff", "#f85149", "#a371f7"

TEXTES = {
    "fr": {"camera": "Caméra\nwebcam ou smartphone", "mouvement": "Mouvement ?", "clip": "Clip MP4\n(+3 s avant)",
           "oiseau": "Oiseau ?\nYOLOS-tiny, puis BioCLIP", "efface": "Clip effacé", "recadre": "Oiseau recadré",
           "bioclip": "BioCLIP\nespèces locales iNaturalist\n+ vos corrections", "micro": "Micro",
           "birdnet": "BirdNET\n+ chants appris", "vote": "Vote sur\ntoute la visite",
           "journal": "Journal, photo,\nstatistiques", "correction": "Correction\n(clic droit)",
           "oui": "oui", "non": "non", "apprend": "apprentissage"},
    "en": {"camera": "Camera\nwebcam or smartphone", "mouvement": "Motion?", "clip": "MP4 clip\n(+3 s before)",
           "oiseau": "Bird?\nYOLOS-tiny, then BioCLIP", "efface": "Clip deleted", "recadre": "Cropped bird",
           "bioclip": "BioCLIP\nlocal iNaturalist species\n+ your corrections", "micro": "Microphone",
           "birdnet": "BirdNET\n+ learned songs", "vote": "Vote over\nthe whole visit",
           "journal": "Log, photo,\nstatistics", "correction": "Correction\n(right-click)",
           "oui": "yes", "non": "no", "apprend": "learning"},
}


def police(taille, gras=False):
    for nom in (["seguisb.ttf", "segoeuib.ttf"] if gras else ["segoeui.ttf"]) + ["DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            pass
    return ImageFont.load_default()


def dessiner(langue):
    t = TEXTES[langue]
    W, H = 1520, 500
    img = Image.new("RGB", (W, H), FOND)
    d = ImageDraw.Draw(img)
    f, fg, fp = police(19), police(20, True), police(16)
    boites = {}

    def boite(cle, cx, cy, couleur, l=210, h=86):
        x0, y0 = cx - l // 2, cy - h // 2
        d.rounded_rectangle([x0, y0, x0 + l, y0 + h], radius=16, fill=CARTE, outline=couleur, width=3)
        lignes = t[cle].split("\n")
        hauteur = len(lignes) * 25
        for i, ligne in enumerate(lignes):
            police_l = fg if i == 0 else f
            lw = d.textlength(ligne, font=police_l)
            d.text((cx - lw / 2, cy - hauteur / 2 + i * 25), ligne, font=police_l,
                   fill=TEXTE if i == 0 else DISCRET)
        boites[cle] = (x0, y0, x0 + l, y0 + h)

    def fleche(a, b, cote_a="d", cote_b="g", couleur=DISCRET, etiquette=None, pointilles=False):
        def point(cle, cote):
            x0, y0, x1, y1 = boites[cle]
            return {"d": (x1, (y0 + y1) / 2), "g": (x0, (y0 + y1) / 2), "h": ((x0 + x1) / 2, y0),
                    "b": ((x0 + x1) / 2, y1)}[cote]
        (xa, ya), (xb, yb) = point(a, cote_a), point(b, cote_b)
        if pointilles:
            n = int(max(abs(xb - xa), abs(yb - ya)) / 14)
            for i in range(0, n, 2):
                d.line([xa + (xb - xa) * i / n, ya + (yb - ya) * i / n,
                        xa + (xb - xa) * (i + 1) / n, ya + (yb - ya) * (i + 1) / n], fill=couleur, width=3)
        else:
            d.line([xa, ya, xb, yb], fill=couleur, width=3)
        import math
        ang = math.atan2(yb - ya, xb - xa)
        d.polygon([(xb, yb), (xb - 14 * math.cos(ang - 0.4), yb - 14 * math.sin(ang - 0.4)),
                   (xb - 14 * math.cos(ang + 0.4), yb - 14 * math.sin(ang + 0.4))], fill=couleur)
        if etiquette:       # au-dessus d'une flèche horizontale, à côté d'une flèche verticale
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            lw = d.textlength(etiquette, font=fp)
            x, y = (mx - lw / 2, my - 30) if abs(xb - xa) > abs(yb - ya) else (mx + 10, my - 11)
            d.text((x, y), etiquette, font=fp, fill=couleur)

    # ligne du haut : image
    boite("camera", 150, 80, BLEU, l=250)
    boite("mouvement", 420, 80, DISCRET, l=180)
    boite("clip", 660, 80, DISCRET, l=190)
    boite("oiseau", 930, 80, AMBRE, l=260)
    boite("efface", 930, 240, ROUGE, l=190, h=60)
    boite("recadre", 1250, 80, AMBRE, l=190, h=70)
    boite("bioclip", 1250, 240, VERT, l=280, h=104)
    # ligne du bas : chants et résultat
    boite("micro", 150, 420, BLEU, l=180, h=64)
    boite("birdnet", 420, 420, VIOLET)
    boite("vote", 930, 420, VERT, l=200)
    boite("journal", 1170, 420, VERT, l=200)
    boite("correction", 1400, 420, BLEU, l=190)

    fleche("camera", "mouvement")
    fleche("mouvement", "clip", etiquette=t["oui"], couleur=VERT)
    fleche("clip", "oiseau")
    fleche("oiseau", "efface", "b", "h", couleur=ROUGE, etiquette=t["non"])
    fleche("oiseau", "recadre", couleur=VERT, etiquette=t["oui"])
    fleche("recadre", "bioclip", "b", "h")
    fleche("bioclip", "vote", "g", "h")
    fleche("micro", "birdnet")
    fleche("birdnet", "vote")
    fleche("vote", "journal")
    fleche("journal", "correction")
    fleche("correction", "bioclip", "h", "d", couleur=BLEU, etiquette=t["apprend"], pointilles=True)
    img.save(ICI / f"schema_{langue}.png")


if __name__ == "__main__":
    for code in TEXTES:
        dessiner(code)
        print("docs/schema_" + code + ".png")
