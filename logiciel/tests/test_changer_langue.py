"""Réglages › Langue : choisir une langue et Enregistrer doit relancer Becquée dans cette langue.
Utilise (et modifie) la vraie configuration ~/.becquee.json : la sauvegarder avant.
python tests/test_changer_langue.py English"""
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import mangeoire_app as m

nom = sys.argv[1] if len(sys.argv) > 1 else "English"
sys.argv = [str(ICI / "mangeoire_app.py")]        # la relance doit ouvrir l'application, pas ce test
m.MODELES = Path(os.environ.get("BECQUEE_MODELES", ICI / "modeles"))
root = tk.Tk()
app = m.App(root)


def choisir():
    app.reglages()
    dlg = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
    combo = next(w for w in dlg.winfo_children() if isinstance(w, ttk.Combobox))   # Langue : la première liste
    combo.set(nom)
    bouton = [w for w in dlg.winfo_children() if isinstance(w, ttk.Button)][-1]   # Enregistrer
    bouton.invoke()


root.after(3000, choisir)
root.mainloop()
print("ancienne fenêtre fermée ; langue enregistrée :", app.cfg["langue"])
