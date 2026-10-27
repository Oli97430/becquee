"""Vérifie les traductions : chaque texte passé à _() existe dans langues.TEXTES, dans toutes les langues,
avec les mêmes champs {..} ; signale aussi les entrées inutilisées.  python tests/verifier_traductions.py"""
import ast
import string
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import langues

utilises, problemes = set(), []
for fichier in ("mangeoire_app.py", "mangeoire_cam.py", "chants_complement.py"):
    arbre = ast.parse((ICI / fichier).read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Name) and noeud.func.id == "_" and noeud.args:
            a = noeud.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                utilises.add(a.value)
            elif not (isinstance(a, ast.Name) or isinstance(a, ast.Subscript)):   # _(espece), _(PAS_UN_OISEAU)
                problemes.append(f"{fichier}:{noeud.lineno} argument non constant")


def champs(t):
    return {c[1] for c in string.Formatter().parse(t) if c[1]}


utilises |= {"Inconnu", "Pas un oiseau"}           # traduits à l'affichage via affichage()
autres = [c for c in langues.LANGUES if c != "fr"]
for texte in sorted(utilises):
    trad = langues.TEXTES.get(texte)
    if trad is None:
        problemes.append(f"sans traduction : {texte!r}")
        continue
    for code in autres:
        if code not in trad:
            problemes.append(f"[{code}] manquant : {texte!r}")
        elif champs(trad[code]) != champs(texte):
            problemes.append(f"[{code}] champs {champs(trad[code])} ≠ {champs(texte)} : {texte!r}")
inutiles = set(langues.TEXTES) - utilises
print(f"{len(utilises)} textes traduits en {len(autres)} langues ; {len(inutiles)} entrées inutilisées")
for t in sorted(inutiles):
    print("  inutilisée :", repr(t))
for p in problemes:
    print("  PROBLÈME :", p)
sys.exit(1 if problemes else 0)
