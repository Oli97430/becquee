# Becquée pour Android

La mangeoire qui reconnaît ses visiteurs, **100 % sur le téléphone ou la tablette** : la caméra filme la
mangeoire, l'appli détecte le mouvement, vérifie qu'il s'agit d'un oiseau, reconnaît l'espèce, enregistre
le clip et la photo, et tient le journal des visites. Ni PC ni serveur : seule la liste des espèces locales
est demandée à iNaturalist quand le réseau est là (gardée 30 jours, liste BirdNET hors ligne).

Même moteur que la version Windows (`logiciel/mangeoire_cam.py`), porté en Kotlin :

| Étape | Windows | Android |
|---|---|---|
| Mouvement | OpenCV MOG2 | MOG2 réécrit en Kotlin (mêmes réglages) |
| Clip avec 3 s d'avant | OpenCV VideoWriter | encodeur H.264 du téléphone (MediaCodec), lancé seulement pendant les visites |
| Oiseau ou pas | YOLOS-tiny + BioCLIP en seconde chance | idem, ONNX Runtime, poids int8 |
| Espèce | BioCLIP zero-shot, a priori log(observations), vote | idem ; vecteurs texte des 11 709 espèces d'oiseaux calculés sur le PC |
| Corrections | mémoire d'exemples (Tip-Adapter) | idem (bouton « Corriger » dans Visites) |
| Journal | `visites.csv` | même fichier, mêmes colonnes |
| Galerie, statistiques | fenêtres Galerie et Statistiques | onglets Galerie et Stats |
| Ménage | clips de plus de 60 jours / 20 Go | idem (réglable), et toujours 1 Go libre sur le téléphone |
| Son | BirdNET sur le micro | son AAC dans les clips (avec les 3 s d'avant) |

Pas encore porté : reconnaissance des chants (BirdNET audio), flux YouTube.

Différences voulues avec la version Windows :
- détecteur d'oiseaux en 384 x 512 au lieu de 512 x 672 : 2,1 fois plus rapide, mêmes visites sur les deux
  vidéos de test ;
- une fois l'espèce sûre (4 fois en tête à 90 % ou plus), BioCLIP n'est plus relancé pendant la visite ;
- avec la caméra, mouvement cherché sur une image de 320 pixels (480 pour un fichier) ;
- la seconde chance BioCLIP (oiseau raté par le détecteur) ignore les zones de mouvement plus grandes que
  la moitié de l'image (téléphone bougé, écran qui défile).

Sur un Galaxy A015 (2024, milieu de gamme) : 460 ms par analyse (détecteur 205 ms + BioCLIP).

## Installer

Copier `app-arm64-v8a-release.apk` sur le téléphone et l'ouvrir (autoriser l'installation d'applis
inconnues). Android 9 ou plus récent ; ~170 Mo.

1. **Réglages** : « Utiliser ma position » (ou saisir latitude / longitude).
2. **Direct** : « Démarrer la caméra », téléphone **couché à l'horizontale** face à la mangeoire. La surveillance continue écran éteint
   (notification « Surveillance de la mangeoire en cours »).
3. **Visites** : toucher une visite pour voir le clip, « Corriger » pour apprendre une espèce.

Fichiers : `Android/data/io.github.oli97430.becquee/files/visites/` (clips, photos, `visites.csv`).
Batterie : laisser le téléphone **branché** ; les réseaux de neurones ne tournent que pendant les visites.

## Construire

Prérequis : JDK 17, SDK Android (Android Studio), et l'environnement Python de `logiciel/`
(celui de la version Windows, avec PyTorch) pour convertir les modèles.

1. Convertir les modèles (une fois, ~5 min ; ils ne sont pas dans git car trop gros) :
   ```bash
   logiciel/venv/Scripts/python -m pip install onnx_ir
   cd android/conversion
   ../../logiciel/venv/Scripts/python convertir_modeles.py
   ```
   Les modèles de la version Windows doivent déjà être dans `logiciel/modeles/` (lancer l'appli Windows une fois).
2. Vérifier les modèles convertis sur la vidéo de test (doit afficher `12/12 espèces justes`) :
   ```bash
   ../../logiciel/venv/Scripts/python valider_modeles.py
   ```
3. Construire les APK :
   ```bash
   cd android
   ./gradlew assembleRelease
   ```
   Résultat dans `app/build/outputs/apk/release/` : `app-arm64-v8a-release.apk` (téléphones, tablettes)
   et `app-x86_64-release.apk` (émulateur du PC).

## Tester sur la vidéo de La Réunion

Sur l'émulateur ou un téléphone branché en USB :

```bash
adb install -r app/build/outputs/apk/release/app-x86_64-release.apk
adb shell cmd locale set-app-locales io.github.oli97430.becquee --locales fr-FR
adb push ../logiciel/tests/videos/mangeoire_reunion.mp4 /sdcard/Android/data/io.github.oli97430.becquee/files/test.mp4
adb shell am start -S -n io.github.oli97430.becquee/.MainActivity --es latitude -21.1 --es longitude 55.5 --es video /sdcard/Android/data/io.github.oli97430.becquee/files/test.mp4
adb logcat -s Becquee
```

Attendu : 12 « Fin de visite » (Martin triste, Astrild ondulé, Foudi rouge, Géopélie zébrée, Bulbul de
Bourbon, Moineau domestique, Tisserin gendarme, Bulbul orphée, Tarier de La Réunion, Tchitrec des
Mascareignes, Zostérops des Mascareignes, Zostérops de la Réunion) et un « Mouvement sans oiseau ».
Sous Git Bash, préfixer les commandes `adb` par `MSYS_NO_PATHCONV=1`. Ajouter `--es direct 1` simule la
caméra : la vidéo est envoyée au moteur en temps réel, comme les images de CameraX (même chemin de code).
`--es acceleration cpu|xnnpack|nnapi --es fils 4` sert aux mesures de vitesse (le processeur seul avec
4 fils est le plus rapide sur le Galaxy A015). Le même test est possible depuis
l'appli : Direct › « Analyser une vidéo ».

## Modèles et quantification

`convertir_modeles.py` exporte l'encodeur d'image de BioCLIP et YOLOS-tiny en ONNX, avec des poids int8
par blocs (MatMulNBits, calculs en float32). La quantification classique (activations int8 aussi) faisait
rater le Bulbul orphée du test (similarité 0,95 avec le modèle d'origine, contre 0,9997 ici).
L'encodeur de texte reste sur le PC : les phrases « a photo of *nom scientifique* (*nom anglais*). » de
toutes les espèces d'oiseaux (BirdNET + iNaturalist) sont précalculées dans `bioclip_textes.bin`.

| Fichier | Taille |
|---|---|
| `bioclip_image.onnx` | 92 Mo |
| `bioclip_textes.bin` | 12 Mo |
| `birdnet_data_model.onnx` (liste hors ligne) | 14 Mo |
| `yolos_tiny.onnx` (entrée 384 x 512) | 11 Mo |

Licences : voir le README principal (BirdNET : usage non commercial). La télémétrie d'ONNX Runtime est
désactivée : aucune image ne quitte le téléphone.
