"""Génère le logo de Becquée : une mésange dont l'œil est un objectif photo.

Produit : becquee.png (512 px), becquee.ico (icône Windows multi-tailles),
becquee_titre.png (logo + nom, pour la notice).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = Path(__file__).resolve().parent
T = 1024  # dessin en haute résolution puis réduction (anticrénelage)


def degrade(taille, haut, bas):
    img = Image.new("RGB", (taille, taille))
    d = ImageDraw.Draw(img)
    for y in range(taille):
        t = y / (taille - 1)
        d.line([(0, y), (taille, y)], fill=tuple(int(h + (b - h) * t) for h, b in zip(haut, bas)))
    return img


def logo():
    # fond : carré arrondi, dégradé vert sapin -> bleu nuit
    fond = degrade(T, (20, 83, 61), (12, 30, 48)).convert("RGBA")
    masque = Image.new("L", (T, T), 0)
    ImageDraw.Draw(masque).rounded_rectangle([0, 0, T - 1, T - 1], radius=230, fill=255)
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    img.paste(fond, mask=masque)

    # ombre portée de l'oiseau
    ombre = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    ImageDraw.Draw(ombre).ellipse([250, 330, 830, 900], fill=(0, 0, 0, 110))
    img = Image.alpha_composite(img, ombre.filter(ImageFilter.GaussianBlur(40)))

    d = ImageDraw.Draw(img)
    # queue
    d.polygon([(700, 690), (905, 600), (920, 650), (740, 770)], fill=(37, 99, 205))
    # corps (ventre jaune mésange)
    d.ellipse([230, 300, 800, 870], fill=(246, 200, 66))
    # aile bleue : ellipse inclinée, avec liseré clair
    aile = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    da = ImageDraw.Draw(aile)
    da.ellipse([420, 560, 860, 760], fill=(59, 130, 246))
    da.ellipse([450, 590, 830, 740], fill=(37, 99, 205))
    da.line([(500, 690), (800, 650)], fill=(147, 197, 253), width=14)
    aile = aile.rotate(28, center=(640, 660), resample=Image.BICUBIC)
    img = Image.alpha_composite(img, aile)
    d = ImageDraw.Draw(img)
    # calotte bleue
    d.chord([230, 300, 800, 870], start=195, end=330, fill=(59, 130, 246))
    # joue blanche
    d.ellipse([270, 400, 560, 640], fill=(250, 250, 245))
    # bandeau noir de l'œil
    d.polygon([(250, 470), (560, 420), (570, 470), (260, 530)], fill=(25, 30, 38))
    # bec
    d.polygon([(232, 520), (130, 560), (236, 590)], fill=(30, 34, 40))
    # graine dans le bec
    d.ellipse([92, 532, 150, 580], fill=(214, 160, 82))

    # œil = objectif photo
    cx, cy, r = 420, 480, 92
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(18, 22, 28))
    d.ellipse([cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18], fill=(70, 78, 92))
    d.ellipse([cx - r + 34, cy - r + 34, cx + r - 34, cy + r - 34], fill=(16, 40, 80))
    d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(56, 132, 255))
    d.ellipse([cx - 40, cy - 52, cx - 8, cy - 20], fill=(235, 245, 255))
    # point rouge "REC"
    d.ellipse([800, 170, 880, 250], fill=(248, 81, 73))
    d.ellipse([800, 170, 880, 250], outline=(255, 255, 255), width=10)
    return img


def main():
    grand = logo()
    petit = grand.resize((512, 512), Image.LANCZOS)
    petit.save(ICI / "becquee.png")
    grand.resize((256, 256), Image.LANCZOS).save(
        ICI / "becquee.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    # logo + nom
    titre = Image.new("RGBA", (1400, 400), (0, 0, 0, 0))
    titre.paste(grand.resize((320, 320), Image.LANCZOS), (30, 40), grand.resize((320, 320), Image.LANCZOS))
    d = ImageDraw.Draw(titre)
    try:
        f1, f2 = ImageFont.truetype("seguisb.ttf", 150), ImageFont.truetype("segoeui.ttf", 50)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    d.text((400, 60), "Becquée", font=f1, fill=(20, 83, 61))
    d.text((408, 255), "la mangeoire qui reconnaît ses visiteurs", font=f2, fill=(90, 100, 110))
    titre.save(ICI / "becquee_titre.png")
    print("logo généré")


if __name__ == "__main__":
    main()
