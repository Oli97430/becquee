"""Ouvre Becquée dans une langue, capture la fenêtre et les Réglages, affiche quelques noms d'espèces.
python tests/test_langues.py <code langue> <dossier des visites> <dossier de sortie>"""
import ctypes
import json
import sys
import tkinter as tk
from pathlib import Path

from PIL import ImageGrab

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import mangeoire_app as m

code, visites, sortie = sys.argv[1], sys.argv[2], Path(sys.argv[3])
sortie.mkdir(parents=True, exist_ok=True)
m.MODELES = Path(__import__("os").environ.get("BECQUEE_MODELES", ICI / "modeles"))   # modèles déjà téléchargés
m.CONFIG = sortie / f"config_{code}.json"
m.CONFIG.write_text(json.dumps({"langue": code, "dossier": visites, "latitude": -21.1, "longitude": 55.5,
                                "lieu": "La Réunion", "ecoute": False}), encoding="utf-8")
ctypes.windll.shcore.SetProcessDpiAwareness(1)
erreurs = []
root = tk.Tk()
root.report_callback_exception = lambda *a: erreurs.append(repr(a[1]))
app = m.App(root)
root.state("normal")
root.geometry("1440x900+0+0")
root.attributes("-topmost", True)


def capture(fenetre, nom):
    fenetre.update()
    x, y = fenetre.winfo_rootx(), fenetre.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + fenetre.winfo_width(), y + fenetre.winfo_height()), all_screens=True).save(sortie / nom)


def etape1():
    capture(root, f"{code}_principale.png")
    app.reglages()
    root.after(800, etape2)


def etape2():
    dlg = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
    dlg.attributes("-topmost", True)
    capture(dlg, f"{code}_reglages.png")
    dlg.destroy()
    print(code, "|", app.lbl_modele.cget("text"), "|", [e["nom"] for e in app.reconnaisseur.especes[:6]], flush=True)
    app.quitter()


root.after(15000, etape1)
root.mainloop()
print(code, "erreurs Tk :", erreurs or "aucune")
