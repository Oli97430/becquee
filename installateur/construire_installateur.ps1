# =====================================================================
#  Becquée — construction de l'installateur Windows complet (hors ligne)
#
#  Prépare dans $Build\app une installation autonome :
#    - Python 3.11 déplaçable (python-build-standalone, Tkinter inclus)
#    - toutes les bibliothèques (PyTorch CPU, OpenCV, transformers, open_clip,
#      onnxruntime, sounddevice, PyAV...)
#    - les modèles (BioCLIP, YOLOS-tiny, BirdNET + noms français, complément des chants)
#    - l'application, son icône, la notice et les fichiers 3D de la mangeoire
#  puis compile becquee.iss avec Inno Setup 6 -> Becquee_Installation.exe
#
#  Utilisation :  powershell -ExecutionPolicy Bypass -File construire_installateur.ps1
# =====================================================================
param(
    [string]$Build = "C:\Users\$env:USERNAME\Becquee_build",
    [string]$Modeles = "C:\Users\$env:USERNAME\Becquee\modeles",      # modèles déjà téléchargés
    [string]$Impression = "",                                          # vide = modele_3d du dépôt
    [string]$PythonUrl = "https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.11.17%2B20261009-x86_64-pc-windows-msvc-install_only.tar.gz"
)
$ErrorActionPreference = "Stop"
$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
$logiciel = Resolve-Path (Join-Path $ici "..\logiciel")
$depot = Resolve-Path (Join-Path $ici "..")
if (-not $Impression) { $Impression = Join-Path $depot "modele_3d" }
$app = Join-Path $Build "app"
$dl = Join-Path $Build "telechargements"
New-Item -ItemType Directory -Force $app, $dl | Out-Null

function Etape($t) { Write-Host "`n=== $t" -ForegroundColor Cyan }

# 1. Python autonome
$py = Join-Path $app "python\python.exe"
if (-not (Test-Path $py)) {
    Etape "Python 3.11 autonome"
    $archive = Join-Path $dl "python.tar.gz"
    if (-not (Test-Path $archive)) { Invoke-WebRequest -UseBasicParsing $PythonUrl -OutFile $archive }
    tar -xzf $archive -C $app            # crée $app\python
    if ($LASTEXITCODE) { throw "extraction de Python impossible" }
}
& $py -c "import tkinter, sys; print('Python', sys.version.split()[0], '- Tk', tkinter.TkVersion)"

# 2. Bibliothèques (PyTorch en version CPU : bien plus léger)
Etape "Bibliothèques"
& $py -m pip install --upgrade --no-warn-script-location --disable-pip-version-check pip
& $py -m pip install --no-warn-script-location --disable-pip-version-check torch torchvision --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE) { throw "installation de PyTorch impossible" }
& $py -m pip install --no-warn-script-location --disable-pip-version-check -r (Join-Path $logiciel "requirements.txt")
if ($LASTEXITCODE) { throw "installation des bibliothèques impossible" }

# 3. Application
Etape "Application"
foreach ($f in "mangeoire_app.py", "mangeoire_cam.py", "chants_complement.py", "langues.py", "becquee.ico", "becquee.png",
               "becquee_titre.png", "requirements.txt") {
    Copy-Item (Join-Path $logiciel $f) $app -Force
}
# notices : README du dépôt (français -> LISEZMOI.md, anglais -> README.en.md)
foreach ($n in @(@("README.md", "LISEZMOI.md"), @("README.en.md", "README.en.md"))) {
    $texte = [IO.File]::ReadAllText((Join-Path $depot $n[0])).Replace("logiciel/becquee_titre.png", "becquee_titre.png")
    [IO.File]::WriteAllText((Join-Path $app $n[1]), $texte, (New-Object Text.UTF8Encoding $false))
}
if (Test-Path $Impression) {        # modèle 3D de la mangeoire : STL, source OpenSCAD et aperçus
    $i3d = Join-Path $app "impression3d"
    if (Test-Path $i3d) { Remove-Item $i3d -Recurse -Force }      # pas de restes d'une construction précédente
    New-Item -ItemType Directory -Force $i3d | Out-Null
    Copy-Item (Join-Path $Impression "stl\*.stl"), (Join-Path $Impression "*.scad"), (Join-Path $Impression "apercus\*.png") $i3d -Force
}

# 4. Modèles BirdNET (+ complément des chants appris, utilisé seulement près de l'endroit appris)
Etape "Modèles BirdNET"
$m = Join-Path $app "modeles"
New-Item -ItemType Directory -Force $m | Out-Null
foreach ($f in "birdnet.onnx", "birdnet_data_model.onnx", "birdnet_empreintes.onnx", "chants_complement.npz",
               "bioclip_textes.npz") {
    if (Test-Path (Join-Path $Modeles $f)) { Copy-Item (Join-Path $Modeles $f) $m -Force }
}
Copy-Item (Join-Path $Modeles "BirdNET_GLOBAL_6K_V2.4_Labels*.txt") $m -Force      # noms d'espèces, toutes langues
Push-Location $app
& $py -c "import mangeoire_cam as m, chants_complement as c; m.Ecoute.telecharger('modeles'); c.preparer_modele_empreintes('modeles'); print('BirdNET OK')"
Pop-Location

# 5. Modèles image (BioCLIP, YOLOS-tiny) dans le cache livré avec l'application
Etape "Modèles image"
$env:HF_HOME = Join-Path $app "hf_cache"
& $py -c "import open_clip; open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip'); open_clip.get_tokenizer('hf-hub:imageomics/bioclip'); from transformers import pipeline; pipeline('object-detection', model='hustvl/yolos-tiny'); print('BioCLIP + YOLOS OK')"
if ($LASTEXITCODE) { throw "téléchargement des modèles image impossible" }
Remove-Item Env:HF_HOME

# 6. Nettoyage
Etape "Nettoyage"
Get-ChildItem $app -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem (Join-Path $app "hf_cache") -Recurse -Directory -Filter ".locks" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
$taille = (Get-ChildItem $app -Recurse -File | Measure-Object Length -Sum).Sum / 1GB
Write-Host ("Application prête : {0:N2} Go" -f $taille)

# 7. Compilation de l'installateur
Etape "Installateur (Inno Setup)"
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 introuvable (https://jrsoftware.org/isdl.php)" }
& $iscc "/DSource=$app" "/O$Build" (Join-Path $ici "becquee.iss")
if ($LASTEXITCODE) { throw "compilation de l'installateur impossible" }
Get-Item (Join-Path $Build "Becquee_Installation.exe") | Select-Object Name, @{n = "Mo"; e = { [int]($_.Length / 1MB) } }
