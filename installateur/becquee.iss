; =====================================================================
;  Becquée — installateur Windows (Inno Setup 6), en 6 langues
;  Tout est inclus : Python, bibliothèques et modèles. Aucune connexion
;  n'est nécessaire pour installer. Installation pour l'utilisateur courant
;  (pas de droits administrateur) : les modèles restent modifiables.
;  La langue choisie ici devient celle de l'application.
;  Compilé par construire_installateur.ps1 (/DSource=<dossier app>).
; =====================================================================
#ifndef Source
  #define Source "C:\Becquee_build\app"
#endif
#define Nom "Becquée"
#define Version "1.1"

[Setup]
AppId={{6F2B1C7E-3D4A-4E59-9B8C-BECQUEE00001}
AppName={#Nom}
AppVersion={#Version}
AppVerName={#Nom} {#Version}
AppPublisher=Becquée
AppComments={cm:Accroche}
DefaultDirName={localappdata}\Programs\Becquee
DefaultGroupName={#Nom}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=Becquee_Installation
SetupIconFile={#Source}\becquee.ico
UninstallDisplayIcon={app}\becquee.ico
UninstallDisplayName={#Nom}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=6
DiskSpanning=no
CloseApplications=yes
ShowLanguageDialog=auto

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"

[Messages]
fr.WelcomeLabel2=Ceci va installer [name] sur votre ordinateur.%n%nTout est inclus (Python, bibliothèques, modèles de reconnaissance des oiseaux et des chants) : aucune connexion Internet n'est nécessaire pour l'installation.%n%nEnviron 3 Go d'espace disque sont nécessaires.
en.WelcomeLabel2=This will install [name] on your computer.%n%nEverything is included (Python, libraries, bird and birdsong recognition models): no Internet connection is needed to install.%n%nAbout 3 GB of disk space is required.
es.WelcomeLabel2=Se instalará [name] en su equipo.%n%nTodo está incluido (Python, bibliotecas, modelos de reconocimiento de aves y de cantos): no se necesita conexión a Internet para instalar.%n%nSe necesitan unos 3 GB de espacio en disco.
de.WelcomeLabel2=[name] wird auf Ihrem Computer installiert.%n%nAlles ist enthalten (Python, Bibliotheken, Modelle zur Erkennung von Vögeln und Gesängen): Für die Installation ist keine Internetverbindung nötig.%n%nEtwa 3 GB Speicherplatz werden benötigt.
pt.WelcomeLabel2=Isto vai instalar o [name] no seu computador.%n%nTudo está incluído (Python, bibliotecas, modelos de reconhecimento de aves e de cantos): não é preciso conexão com a Internet para instalar.%n%nSão necessários cerca de 3 GB de espaço em disco.
it.WelcomeLabel2=Verrà installato [name] sul computer.%n%nÈ tutto incluso (Python, librerie, modelli di riconoscimento degli uccelli e dei canti): non serve una connessione a Internet per l'installazione.%n%nSono necessari circa 3 GB di spazio su disco.

[CustomMessages]
fr.Accroche=La mangeoire qui reconnaît ses visiteurs
en.Accroche=The bird feeder that knows its visitors
es.Accroche=El comedero que reconoce a sus visitantes
de.Accroche=Das Futterhaus, das seine Besucher erkennt
pt.Accroche=O comedouro que reconhece seus visitantes
it.Accroche=La mangiatoia che riconosce i suoi visitatori
fr.Raccourcis=Raccourcis :
en.Raccourcis=Shortcuts:
es.Raccourcis=Accesos directos:
de.Raccourcis=Verknüpfungen:
pt.Raccourcis=Atalhos:
it.Raccourcis=Collegamenti:
fr.Bureau=Créer un raccourci sur le Bureau
en.Bureau=Create a desktop shortcut
es.Bureau=Crear un acceso directo en el escritorio
de.Bureau=Verknüpfung auf dem Desktop erstellen
pt.Bureau=Criar um atalho na área de trabalho
it.Bureau=Crea un collegamento sul desktop
fr.Demarrage=Lancer Becquée à l'ouverture de Windows
en.Demarrage=Start Becquée when Windows starts
es.Demarrage=Iniciar Becquée al arrancar Windows
de.Demarrage=Becquée beim Start von Windows öffnen
pt.Demarrage=Iniciar o Becquée com o Windows
it.Demarrage=Avvia Becquée all'avvio di Windows
fr.Fichiers3D=fichiers 3D de la mangeoire
en.Fichiers3D=3D files of the feeder
es.Fichiers3D=archivos 3D del comedero
de.Fichiers3D=3D-Dateien des Futterhauses
pt.Fichiers3D=arquivos 3D do comedouro
it.Fichiers3D=file 3D della mangiatoia
fr.Notice=notice
en.Notice=guide
es.Notice=guía
de.Notice=Anleitung
pt.Notice=guia
it.Notice=guida
fr.Lancer=Lancer Becquée
en.Lancer=Launch Becquée
es.Lancer=Abrir Becquée
de.Lancer=Becquée starten
pt.Lancer=Abrir o Becquée
it.Lancer=Avvia Becquée

[Tasks]
Name: "bureau"; Description: "{cm:Bureau}"; GroupDescription: "{cm:Raccourcis}"
Name: "demarrage"; Description: "{cm:Demarrage}"; GroupDescription: "{cm:Raccourcis}"; Flags: unchecked

[Files]
Source: "{#Source}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#Nom}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\mangeoire_app.py"""; WorkingDir: "{app}"; IconFilename: "{app}\becquee.ico"; Comment: "{cm:Accroche}"
Name: "{autodesktop}\{#Nom}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\mangeoire_app.py"""; WorkingDir: "{app}"; IconFilename: "{app}\becquee.ico"; Tasks: bureau
Name: "{userstartup}\{#Nom}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\mangeoire_app.py"""; WorkingDir: "{app}"; IconFilename: "{app}\becquee.ico"; Tasks: demarrage
Name: "{autoprograms}\{#Nom} - {cm:Fichiers3D}"; Filename: "{app}\impression3d"
Name: "{autoprograms}\{#Nom} - {cm:Notice}"; Filename: "{app}\LISEZMOI.md"

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\mangeoire_app.py"""; WorkingDir: "{app}"; Description: "{cm:Lancer}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; fichiers créés après l'installation (caches, modèles appris) ; vos vidéos et réglages sont conservés
Type: filesandordirs; Name: "{app}\modeles"
Type: filesandordirs; Name: "{app}\hf_cache"
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
{ Première installation : la langue choisie dans l'installateur devient celle de l'application.
  Une configuration existante n'est pas modifiée (la langue se change dans Réglages). }
procedure CurStepChanged(CurStep: TSetupStep);
var
  Config: String;
begin
  if CurStep = ssPostInstall then
  begin
    Config := ExpandConstant('{%USERPROFILE}\.becquee.json');
    if not FileExists(Config) then
      SaveStringToFile(Config, '{"langue": "' + ActiveLanguage() + '"}', False);
  end;
end;
