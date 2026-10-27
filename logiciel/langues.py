"""
Becquée — langues de l'interface.

Les textes sont écrits en français dans le code et traduits ici : _("Texte {x}", x=...) renvoie la
traduction dans la langue choisie (à défaut le français), avec les valeurs insérées.
Les noms d'espèces, eux, viennent directement dans la bonne langue (iNaturalist et étiquettes BirdNET).

Ajouter une langue : un code dans LANGUES, sa traduction dans chaque entrée de TEXTES, le code iNaturalist
(LOCALE_INATURALIST) et le fichier d'étiquettes BirdNET (ETIQUETTES_BIRDNET).
"""

LANGUES = {"fr": "Français", "en": "English", "es": "Español", "de": "Deutsch", "pt": "Português", "it": "Italiano"}
LOCALE_INATURALIST = {"fr": "fr", "en": "en", "es": "es", "de": "de", "pt": "pt-BR", "it": "it"}
# suffixe des étiquettes BirdNET traduites (projet BirdNET-Go) ; None = étiquettes anglaises d'origine
ETIQUETTES_BIRDNET = {"fr": "fr", "en": None, "es": "es", "de": "de", "pt": "pt_BR", "it": "it"}

langue = "fr"


def regler(code):
    global langue
    langue = code if code in LANGUES else "en"


def langue_systeme():
    """Langue de Windows (ou du système) si elle est proposée, sinon l'anglais."""
    try:
        import ctypes
        import locale
        nom = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "")
    except Exception:
        import locale
        nom = (locale.getlocale()[0] or "")
    code = nom.split("_")[0].lower()
    return code if code in LANGUES else "en"


def _(texte, **valeurs):
    t = TEXTES.get(texte, {}).get(langue, texte) if langue != "fr" else texte
    return t.format(**valeurs) if valeurs else t


TEXTES = {
    # ------------------------------------------------------------ en-tête, barre d'outils
    "la mangeoire qui reconnaît ses visiteurs": {
        "en": "the bird feeder that knows its visitors", "es": "el comedero que reconoce a sus visitantes",
        "de": "das Futterhaus, das seine Besucher erkennt", "pt": "o comedouro que reconhece seus visitantes",
        "it": "la mangiatoia che riconosce i suoi visitatori"},
    "●  En veille": {"en": "●  Idle", "es": "●  En espera", "de": "●  Bereit", "pt": "●  Em espera", "it": "●  In attesa"},
    "●  Connexion…": {"en": "●  Connecting…", "es": "●  Conectando…", "de": "●  Verbinde…", "pt": "●  Conectando…",
                      "it": "●  Connessione…"},
    "●  Visite en cours": {"en": "●  Visit in progress", "es": "●  Visita en curso", "de": "●  Besuch läuft",
                           "pt": "●  Visita em andamento", "it": "●  Visita in corso"},
    "●  Surveillance": {"en": "●  Watching", "es": "●  Vigilando", "de": "●  Überwachung", "pt": "●  Vigiando",
                        "it": "●  Sorveglianza"},
    "Modèle : chargement…": {"en": "Model: loading…", "es": "Modelo: cargando…", "de": "Modell: wird geladen…",
                             "pt": "Modelo: carregando…", "it": "Modello: caricamento…"},
    "Chargement des modèles…": {"en": "Loading models…", "es": "Cargando modelos…", "de": "Modelle werden geladen…",
                                "pt": "Carregando modelos…", "it": "Caricamento dei modelli…"},
    "Modèles prêts · {n} espèces locales": {
        "en": "Models ready · {n} local species", "es": "Modelos listos · {n} especies locales",
        "de": "Modelle bereit · {n} lokale Arten", "pt": "Modelos prontos · {n} espécies locais",
        "it": "Modelli pronti · {n} specie locali"},
    " · photos apprises : {n}": {"en": " · learned photos: {n}", "es": " · fotos aprendidas: {n}",
                                 "de": " · gelernte Fotos: {n}", "pt": " · fotos aprendidas: {n}",
                                 "it": " · foto apprese: {n}"},
    "Modèle indisponible ({erreur})": {"en": "Model unavailable ({erreur})", "es": "Modelo no disponible ({erreur})",
                                       "de": "Modell nicht verfügbar ({erreur})", "pt": "Modelo indisponível ({erreur})",
                                       "it": "Modello non disponibile ({erreur})"},
    "Caméra": {"en": "Camera", "es": "Cámara", "de": "Kamera", "pt": "Câmera", "it": "Fotocamera"},
    "▶  Démarrer": {"en": "▶  Start", "es": "▶  Iniciar", "de": "▶  Starten", "pt": "▶  Iniciar", "it": "▶  Avvia"},
    "■  Arrêter": {"en": "■  Stop", "es": "■  Detener", "de": "■  Stoppen", "pt": "■  Parar", "it": "■  Ferma"},
    "📷  Photo": {"en": "📷  Snapshot", "es": "📷  Foto", "de": "📷  Foto", "pt": "📷  Foto", "it": "📷  Foto"},
    "📁  Dossier": {"en": "📁  Folder", "es": "📁  Carpeta", "de": "📁  Ordner", "pt": "📁  Pasta", "it": "📁  Cartella"},
    "⚙  Réglages": {"en": "⚙  Settings", "es": "⚙  Ajustes", "de": "⚙  Einstellungen", "pt": "⚙  Ajustes",
                    "it": "⚙  Impostazioni"},
    # ------------------------------------------------------------ colonne de droite
    "Dernière visite": {"en": "Last visit", "es": "Última visita", "de": "Letzter Besuch", "pt": "Última visita",
                        "it": "Ultima visita"},
    "Aucune visite pour l'instant": {"en": "No visits yet", "es": "Aún no hay visitas", "de": "Noch keine Besuche",
                                     "pt": "Nenhuma visita ainda", "it": "Ancora nessuna visita"},
    "Aujourd'hui": {"en": "Today", "es": "Hoy", "de": "Heute", "pt": "Hoje", "it": "Oggi"},
    "visites": {"en": "visits", "es": "visitas", "de": "Besuche", "pt": "visitas", "it": "visite"},
    "Visites": {"en": "Visits", "es": "Visitas", "de": "Besuche", "pt": "Visitas", "it": "Visite"},
    "Chants entendus": {"en": "Songs heard", "es": "Cantos oídos", "de": "Gehörte Gesänge", "pt": "Cantos ouvidos",
                        "it": "Canti sentiti"},
    "HEURE": {"en": "TIME", "es": "HORA", "de": "ZEIT", "pt": "HORA", "it": "ORA"},
    "QUAND": {"en": "WHEN", "es": "CUÁNDO", "de": "WANN", "pt": "QUANDO", "it": "QUANDO"},
    "ESPÈCE": {"en": "SPECIES", "es": "ESPECIE", "de": "ART", "pt": "ESPÉCIE", "it": "SPECIE"},
    "CONF.": {"en": "CONF.", "es": "CONF.", "de": "SICH.", "pt": "CONF.", "it": "CONF."},
    "Clic droit sur une visite pour corriger l'espèce": {
        "en": "Right-click a visit to correct the species", "es": "Clic derecho en una visita para corregir la especie",
        "de": "Rechtsklick auf einen Besuch, um die Art zu korrigieren",
        "pt": "Clique com o botão direito numa visita para corrigir a espécie",
        "it": "Clic destro su una visita per correggere la specie"},
    "Pas encore de visite aujourd'hui": {"en": "No visits today yet", "es": "Todavía no hay visitas hoy",
                                         "de": "Heute noch keine Besuche", "pt": "Nenhuma visita hoje ainda",
                                         "it": "Ancora nessuna visita oggi"},
    "{jour}/{mois} à {heure}": {"en": "{mois}/{jour} at {heure}", "es": "{jour}/{mois} a las {heure}",
                                "de": "{jour}.{mois}. um {heure}", "pt": "{jour}/{mois} às {heure}",
                                "it": "{jour}/{mois} alle {heure}"},
    "par l'image": {"en": "by image", "es": "por la imagen", "de": "per Bild", "pt": "pela imagem", "it": "dall'immagine"},
    "par le chant": {"en": "by song", "es": "por el canto", "de": "per Gesang", "pt": "pelo canto", "it": "dal canto"},
    "image + chant": {"en": "image + song", "es": "imagen + canto", "de": "Bild + Gesang", "pt": "imagem + canto",
                      "it": "immagine + canto"},
    "corrigé à la main": {"en": "corrected by hand", "es": "corregido a mano", "de": "von Hand korrigiert",
                          "pt": "corrigido à mão", "it": "corretto a mano"},
    "Chants entendus : {liste}": {"en": "Songs heard: {liste}", "es": "Cantos oídos: {liste}",
                                  "de": "Gehörte Gesänge: {liste}", "pt": "Cantos ouvidos: {liste}",
                                  "it": "Canti sentiti: {liste}"},
    "Inconnu": {"en": "Unknown", "es": "Desconocido", "de": "Unbekannt", "pt": "Desconhecido", "it": "Sconosciuto"},
    "Pas un oiseau": {"en": "Not a bird", "es": "No es un ave", "de": "Kein Vogel", "pt": "Não é uma ave",
                      "it": "Non è un uccello"},
    # ------------------------------------------------------------ correction
    "Corriger « {espece} » en :": {"en": "Correct “{espece}” to:", "es": "Corregir «{espece}» a:",
                                   "de": "„{espece}“ korrigieren in:", "pt": "Corrigir “{espece}” para:",
                                   "it": "Correggi «{espece}» in:"},
    "Autre espèce…": {"en": "Other species…", "es": "Otra especie…", "de": "Andere Art…", "pt": "Outra espécie…",
                      "it": "Altra specie…"},
    "Corriger": {"en": "Correct", "es": "Corregir", "de": "Korrigieren", "pt": "Corrigir", "it": "Correggi"},
    "Nom de l'espèce (commun ou scientifique) :": {
        "en": "Species name (common or scientific):", "es": "Nombre de la especie (común o científico):",
        "de": "Name der Art (deutsch oder wissenschaftlich):", "pt": "Nome da espécie (comum ou científico):",
        "it": "Nome della specie (comune o scientifico):"},
    "Corrigé : {espece} — Becquée apprend de cette photo…": {
        "en": "Corrected: {espece} — Becquée is learning from this photo…",
        "es": "Corregido: {espece} — Becquée aprende de esta foto…",
        "de": "Korrigiert: {espece} — Becquée lernt aus diesem Foto…",
        "pt": "Corrigido: {espece} — Becquée aprende com esta foto…",
        "it": "Corretto: {espece} — Becquée impara da questa foto…"},
    "Appris — photos corrigées : {n}, espèces : {e}": {
        "en": "Learned — corrected photos: {n}, species: {e}", "es": "Aprendido — fotos corregidas: {n}, especies: {e}",
        "de": "Gelernt — korrigierte Fotos: {n}, Arten: {e}", "pt": "Aprendido — fotos corrigidas: {n}, espécies: {e}",
        "it": "Appreso — foto corrette: {n}, specie: {e}"},
    "Apprentissage impossible ({erreur})": {"en": "Learning failed ({erreur})", "es": "Aprendizaje imposible ({erreur})",
                                            "de": "Lernen fehlgeschlagen ({erreur})", "pt": "Aprendizado impossível ({erreur})",
                                            "it": "Apprendimento impossibile ({erreur})"},
    # ------------------------------------------------------------ pied de fenêtre
    "Sensibilité": {"en": "Sensitivity", "es": "Sensibilidad", "de": "Empfindlichkeit", "pt": "Sensibilidade",
                    "it": "Sensibilità"},
    "Seuil de reconnaissance": {"en": "Recognition threshold", "es": "Umbral de reconocimiento",
                                "de": "Erkennungsschwelle", "pt": "Limiar de reconhecimento", "it": "Soglia di riconoscimento"},
    "Reconnaissance": {"en": "Recognition", "es": "Reconocimiento", "de": "Erkennung", "pt": "Reconhecimento",
                       "it": "Riconoscimento"},
    "Oiseaux seulement": {"en": "Birds only", "es": "Solo aves", "de": "Nur Vögel", "pt": "Só aves", "it": "Solo uccelli"},
    "Écoute des chants": {"en": "Listen to songs", "es": "Escuchar cantos", "de": "Gesänge hören", "pt": "Ouvir cantos",
                          "it": "Ascolto dei canti"},
    "Prêt": {"en": "Ready", "es": "Listo", "de": "Bereit", "pt": "Pronto", "it": "Pronto"},
    "Micro muet : vérifiez Paramètres › Son › Entrée": {
        "en": "Microphone silent: check Settings › Sound › Input",
        "es": "Micrófono mudo: revise Configuración › Sonido › Entrada",
        "de": "Mikrofon stumm: Einstellungen › Sound › Eingabe prüfen",
        "pt": "Microfone mudo: verifique Configurações › Som › Entrada",
        "it": "Microfono muto: controlla Impostazioni › Audio › Input"},
    "Démarrez la surveillance pour prendre une photo": {
        "en": "Start watching to take a snapshot", "es": "Inicie la vigilancia para tomar una foto",
        "de": "Starten Sie die Überwachung, um ein Foto zu machen", "pt": "Inicie a vigilância para tirar uma foto",
        "it": "Avvia la sorveglianza per scattare una foto"},
    "Photo enregistrée : {nom}": {"en": "Snapshot saved: {nom}", "es": "Foto guardada: {nom}",
                                  "de": "Foto gespeichert: {nom}", "pt": "Foto salva: {nom}", "it": "Foto salvata: {nom}"},
    "Becquée — enregistrement de la visite en cours…": {
        "en": "Becquée — saving the current visit…", "es": "Becquée — guardando la visita en curso…",
        "de": "Becquée — laufender Besuch wird gespeichert…", "pt": "Becquée — salvando a visita em andamento…",
        "it": "Becquée — salvataggio della visita in corso…"},
    # ------------------------------------------------------------ vidéo
    "Cliquez sur « Démarrer » pour lancer la surveillance": {
        "en": "Click “Start” to begin watching", "es": "Haga clic en «Iniciar» para empezar la vigilancia",
        "de": "Klicken Sie auf „Starten“, um die Überwachung zu beginnen",
        "pt": "Clique em “Iniciar” para começar a vigilância", "it": "Fai clic su «Avvia» per iniziare la sorveglianza"},
    "Chant : {espece}  {conf}": {"en": "Song: {espece}  {conf}", "es": "Canto: {espece}  {conf}",
                                 "de": "Gesang: {espece}  {conf}", "pt": "Canto: {espece}  {conf}",
                                 "it": "Canto: {espece}  {conf}"},
    "{fps} i/s": {"en": "{fps} fps", "es": "{fps} fps", "de": "{fps} B/s", "pt": "{fps} fps", "it": "{fps} fps"},
    # ------------------------------------------------------------ réglages
    "Réglages — Becquée": {"en": "Settings — Becquée", "es": "Ajustes — Becquée", "de": "Einstellungen — Becquée",
                           "pt": "Ajustes — Becquée", "it": "Impostazioni — Becquée"},
    "Langue": {"en": "Language", "es": "Idioma", "de": "Sprache", "pt": "Idioma", "it": "Lingua"},
    "Langue de l'interface et des noms d'espèces (redémarre Becquée).": {
        "en": "Language of the interface and species names (restarts Becquée).",
        "es": "Idioma de la interfaz y de los nombres de especies (reinicia Becquée).",
        "de": "Sprache der Oberfläche und der Artnamen (startet Becquée neu).",
        "pt": "Idioma da interface e dos nomes das espécies (reinicia o Becquée).",
        "it": "Lingua dell'interfaccia e dei nomi delle specie (riavvia Becquée)."},
    "Position de la mangeoire": {"en": "Feeder location", "es": "Ubicación del comedero", "de": "Standort des Futterhauses",
                                 "pt": "Localização do comedouro", "it": "Posizione della mangiatoia"},
    "Ville, commune ou adresse — n'importe où dans le monde.": {
        "en": "City, town or address — anywhere in the world.", "es": "Ciudad, municipio o dirección — en cualquier lugar del mundo.",
        "de": "Stadt, Gemeinde oder Adresse — überall auf der Welt.", "pt": "Cidade, município ou endereço — em qualquer lugar do mundo.",
        "it": "Città, comune o indirizzo — ovunque nel mondo."},
    "Recherche…": {"en": "Searching…", "es": "Buscando…", "de": "Suche…", "pt": "Pesquisando…", "it": "Ricerca…"},
    "Recherche impossible ({erreur}) : saisissez latitude et longitude.": {
        "en": "Search failed ({erreur}): enter latitude and longitude.",
        "es": "Búsqueda imposible ({erreur}): introduzca latitud y longitud.",
        "de": "Suche fehlgeschlagen ({erreur}): Breiten- und Längengrad eingeben.",
        "pt": "Pesquisa impossível ({erreur}): digite latitude e longitude.",
        "it": "Ricerca impossibile ({erreur}): inserisci latitudine e longitudine."},
    "Lieu introuvable : précisez (ex. « Saint-Pierre, La Réunion »).": {
        "en": "Place not found: be more specific (e.g. “Springfield, Illinois”).",
        "es": "Lugar no encontrado: precise más (p. ej. «Santiago, Chile»).",
        "de": "Ort nicht gefunden: bitte genauer (z. B. „Freiburg, Breisgau“).",
        "pt": "Local não encontrado: seja mais preciso (ex. “Viçosa, Minas Gerais”).",
        "it": "Luogo non trovato: sii più preciso (es. «San Giovanni, Roma»)."},
    "Chercher": {"en": "Search", "es": "Buscar", "de": "Suchen", "pt": "Pesquisar", "it": "Cerca"},
    "Latitude": {"en": "Latitude", "es": "Latitud", "de": "Breitengrad", "pt": "Latitude", "it": "Latitudine"},
    "Longitude": {"en": "Longitude", "es": "Longitud", "de": "Längengrad", "pt": "Longitude", "it": "Longitudine"},
    "Becquée ne propose que les oiseaux observés autour de ce point (liste iNaturalist, mise à jour chaque mois) : "
    "la reconnaissance est bien plus fiable.": {
        "en": "Becquée only suggests birds observed around this point (iNaturalist list, updated monthly): "
              "recognition is much more reliable.",
        "es": "Becquée solo propone las aves observadas alrededor de este punto (lista de iNaturalist, actualizada "
              "cada mes): el reconocimiento es mucho más fiable.",
        "de": "Becquée schlägt nur Vögel vor, die rund um diesen Ort beobachtet wurden (iNaturalist-Liste, monatlich "
              "aktualisiert): Die Erkennung ist so viel zuverlässiger.",
        "pt": "O Becquée só propõe as aves observadas em torno deste ponto (lista do iNaturalist, atualizada todo mês): "
              "o reconhecimento fica muito mais confiável.",
        "it": "Becquée propone solo gli uccelli osservati intorno a questo punto (elenco iNaturalist, aggiornato ogni "
              "mese): il riconoscimento è molto più affidabile."},
    "Enregistrement": {"en": "Recording", "es": "Grabación", "de": "Aufnahme", "pt": "Gravação", "it": "Registrazione"},
    "Parcourir…": {"en": "Browse…", "es": "Examinar…", "de": "Durchsuchen…", "pt": "Procurar…", "it": "Sfoglia…"},
    "Garder aussi les mouvements sans oiseau (déconseillé)": {
        "en": "Also keep motion without a bird (not recommended)", "es": "Guardar también los movimientos sin ave (no recomendado)",
        "de": "Auch Bewegungen ohne Vogel behalten (nicht empfohlen)", "pt": "Manter também movimentos sem ave (não recomendado)",
        "it": "Conserva anche i movimenti senza uccelli (sconsigliato)"},
    "Démarrer la surveillance à l'ouverture": {"en": "Start watching on launch", "es": "Iniciar la vigilancia al abrir",
                                               "de": "Überwachung beim Öffnen starten", "pt": "Iniciar a vigilância ao abrir",
                                               "it": "Avvia la sorveglianza all'apertura"},
    "Ménage automatique (0 = jamais)": {"en": "Automatic cleanup (0 = never)", "es": "Limpieza automática (0 = nunca)",
                                        "de": "Automatisches Aufräumen (0 = nie)", "pt": "Limpeza automática (0 = nunca)",
                                        "it": "Pulizia automatica (0 = mai)"},
    "Effacer les clips de plus de (jours)": {"en": "Delete clips older than (days)", "es": "Borrar clips de más de (días)",
                                             "de": "Clips löschen, älter als (Tage)", "pt": "Apagar clipes com mais de (dias)",
                                             "it": "Elimina clip più vecchie di (giorni)"},
    "Taille maximale du dossier (Go)": {"en": "Maximum folder size (GB)", "es": "Tamaño máximo de la carpeta (GB)",
                                        "de": "Maximale Ordnergröße (GB)", "pt": "Tamanho máximo da pasta (GB)",
                                        "it": "Dimensione massima della cartella (GB)"},
    "Chants (BirdNET)": {"en": "Songs (BirdNET)", "es": "Cantos (BirdNET)", "de": "Gesänge (BirdNET)",
                         "pt": "Cantos (BirdNET)", "it": "Canti (BirdNET)"},
    "Micro": {"en": "Microphone", "es": "Micrófono", "de": "Mikrofon", "pt": "Microfone", "it": "Microfono"},
    "Micro par défaut de Windows": {"en": "Windows default microphone", "es": "Micrófono predeterminado de Windows",
                                    "de": "Windows-Standardmikrofon", "pt": "Microfone padrão do Windows",
                                    "it": "Microfono predefinito di Windows"},
    "Seuil de confiance des chants (%)": {"en": "Song confidence threshold (%)", "es": "Umbral de confianza de los cantos (%)",
                                          "de": "Vertrauensschwelle der Gesänge (%)", "pt": "Limiar de confiança dos cantos (%)",
                                          "it": "Soglia di confidenza dei canti (%)"},
    "Clé API xeno-canto (facultative)": {"en": "xeno-canto API key (optional)", "es": "Clave API de xeno-canto (opcional)",
                                         "de": "xeno-canto-API-Schlüssel (optional)", "pt": "Chave API do xeno-canto (opcional)",
                                         "it": "Chiave API xeno-canto (facoltativa)"},
    "Réglez d'abord la position de la mangeoire.": {
        "en": "Set the feeder location first.", "es": "Primero indique la ubicación del comedero.",
        "de": "Legen Sie zuerst den Standort des Futterhauses fest.", "pt": "Defina primeiro a localização do comedouro.",
        "it": "Imposta prima la posizione della mangiatoia."},
    "Apprentissage en cours (plusieurs minutes)… voir la barre d'état.": {
        "en": "Learning in progress (several minutes)… see the status bar.",
        "es": "Aprendizaje en curso (varios minutos)… vea la barra de estado.",
        "de": "Lernen läuft (mehrere Minuten)… siehe Statusleiste.",
        "pt": "Aprendizado em andamento (vários minutos)… veja a barra de status.",
        "it": "Apprendimento in corso (alcuni minuti)… vedi la barra di stato."},
    "Compléter les chants": {"en": "Learn missing songs", "es": "Completar los cantos", "de": "Gesänge ergänzen",
                             "pt": "Completar os cantos", "it": "Completa i canti"},
    "Smartphone : appli « IP Webcam » (Android), adresse du type http://192.168.1.20:8080/video.\n"
    "Caméra sur Internet (nid, mangeoire) : collez l'adresse de la page YouTube ou du flux,\n"
    "et réglez la position sur le lieu de la caméra. Le micro du PC n'est pas utilisé pour ses visites.\n"
    "L'écoute utilise le micro du PC (ou de la webcam USB).": {
        "en": "Smartphone: “IP Webcam” app (Android), address like http://192.168.1.20:8080/video.\n"
              "Camera on the Internet (nest, feeder): paste the address of the YouTube page or of the stream,\n"
              "and set the position to the camera's location. The PC microphone is not used for its visits.\n"
              "Listening uses the PC microphone (or the USB webcam's).",
        "es": "Smartphone: app «IP Webcam» (Android), dirección del tipo http://192.168.1.20:8080/video.\n"
              "Cámara en Internet (nido, comedero): pegue la dirección de la página de YouTube o del flujo,\n"
              "y ajuste la posición al lugar de la cámara. El micrófono del PC no se usa para sus visitas.\n"
              "La escucha usa el micrófono del PC (o de la webcam USB).",
        "de": "Smartphone: App „IP Webcam“ (Android), Adresse wie http://192.168.1.20:8080/video.\n"
              "Kamera im Internet (Nest, Futterhaus): Adresse der YouTube-Seite oder des Streams einfügen\n"
              "und den Standort auf den Ort der Kamera setzen. Das PC-Mikrofon wird für ihre Besuche nicht verwendet.\n"
              "Zum Hören wird das Mikrofon des PCs (oder der USB-Webcam) verwendet.",
        "pt": "Smartphone: app “IP Webcam” (Android), endereço do tipo http://192.168.1.20:8080/video.\n"
              "Câmera na Internet (ninho, comedouro): cole o endereço da página do YouTube ou do fluxo,\n"
              "e ajuste a posição para o local da câmera. O microfone do PC não é usado para as suas visitas.\n"
              "A escuta usa o microfone do PC (ou da webcam USB).",
        "it": "Smartphone: app «IP Webcam» (Android), indirizzo come http://192.168.1.20:8080/video.\n"
              "Videocamera su Internet (nido, mangiatoia): incolli l'indirizzo della pagina YouTube o del flusso,\n"
              "e imposti la posizione sul luogo della videocamera. Il microfono del PC non è usato per le sue visite.\n"
              "L'ascolto usa il microfono del PC (o della webcam USB)."},
    "Enregistrer": {"en": "Save", "es": "Guardar", "de": "Speichern", "pt": "Salvar", "it": "Salva"},
    "Espèces locales absentes de BirdNET (endémiques…) : Becquée apprend leurs chants (iNaturalist, xeno-canto, "
    "sons gardés lors des visites reconnues à l'image).": {
        "en": "Local species missing from BirdNET (endemics…): Becquée learns their songs (iNaturalist, xeno-canto, "
              "sounds kept from visits recognized by image).",
        "es": "Especies locales ausentes de BirdNET (endémicas…): Becquée aprende sus cantos (iNaturalist, xeno-canto, "
              "sonidos guardados de las visitas reconocidas por imagen).",
        "de": "Lokale Arten, die BirdNET nicht kennt (Endemiten…): Becquée lernt ihre Gesänge (iNaturalist, xeno-canto, "
              "Töne von per Bild erkannten Besuchen).",
        "pt": "Espécies locais ausentes do BirdNET (endêmicas…): o Becquée aprende seus cantos (iNaturalist, xeno-canto, "
              "sons guardados das visitas reconhecidas pela imagem).",
        "it": "Specie locali assenti da BirdNET (endemiche…): Becquée impara i loro canti (iNaturalist, xeno-canto, "
              "suoni conservati dalle visite riconosciute dall'immagine)."},
    "Déjà appris : {n} espèces (le {date}).": {"en": "Already learned: {n} species ({date}).",
                                               "es": "Ya aprendidas: {n} especies ({date}).",
                                               "de": "Bereits gelernt: {n} Arten ({date}).",
                                               "pt": "Já aprendidas: {n} espécies ({date}).",
                                               "it": "Già apprese: {n} specie ({date})."},
    "Appris : {n} espèces. Seuil {seuil} (fausses alertes {fa}).": {
        "en": "Learned: {n} species. Threshold {seuil} (false alarms {fa}).",
        "es": "Aprendidas: {n} especies. Umbral {seuil} (falsas alarmas {fa}).",
        "de": "Gelernt: {n} Arten. Schwelle {seuil} (Fehlalarme {fa}).",
        "pt": "Aprendidas: {n} espécies. Limiar {seuil} (falsos alarmes {fa}).",
        "it": "Apprese: {n} specie. Soglia {seuil} (falsi allarmi {fa})."},
    "Modèle BirdNET en cours de téléchargement…": {"en": "BirdNET model downloading…", "es": "Descargando el modelo BirdNET…",
                                                   "de": "BirdNET-Modell wird heruntergeladen…",
                                                   "pt": "Baixando o modelo BirdNET…", "it": "Download del modello BirdNET…"},
    # ------------------------------------------------------------ messages du moteur
    "Espèces locales : {n} (iNaturalist, rayon {rayon} km)": {
        "en": "Local species: {n} (iNaturalist, {rayon} km radius)", "es": "Especies locales: {n} (iNaturalist, radio {rayon} km)",
        "de": "Lokale Arten: {n} (iNaturalist, Umkreis {rayon} km)", "pt": "Espécies locais: {n} (iNaturalist, raio {rayon} km)",
        "it": "Specie locali: {n} (iNaturalist, raggio {rayon} km)"},
    "Liste iNaturalist indisponible ({erreur}) : liste BirdNET": {
        "en": "iNaturalist list unavailable ({erreur}): using BirdNET list",
        "es": "Lista de iNaturalist no disponible ({erreur}): lista de BirdNET",
        "de": "iNaturalist-Liste nicht verfügbar ({erreur}): BirdNET-Liste",
        "pt": "Lista do iNaturalist indisponível ({erreur}): lista do BirdNET",
        "it": "Elenco iNaturalist non disponibile ({erreur}): elenco BirdNET"},
    "Préparation de {n} espèces (une seule fois)...": {
        "en": "Preparing {n} species (only once)...", "es": "Preparando {n} especies (solo una vez)...",
        "de": "{n} Arten werden vorbereitet (nur einmal)...", "pt": "Preparando {n} espécies (só uma vez)...",
        "it": "Preparazione di {n} specie (una sola volta)..."},
    "Chants : {n} espèces locales ajoutées à BirdNET": {
        "en": "Songs: {n} local species added to BirdNET", "es": "Cantos: {n} especies locales añadidas a BirdNET",
        "de": "Gesänge: {n} lokale Arten zu BirdNET hinzugefügt", "pt": "Cantos: {n} espécies locais adicionadas ao BirdNET",
        "it": "Canti: {n} specie locali aggiunte a BirdNET"},
    "Complément des chants indisponible ({erreur})": {
        "en": "Song add-on unavailable ({erreur})", "es": "Complemento de cantos no disponible ({erreur})",
        "de": "Gesangsergänzung nicht verfügbar ({erreur})", "pt": "Complemento de cantos indisponível ({erreur})",
        "it": "Complemento dei canti non disponibile ({erreur})"},
    "Chants : {n} espèces possibles ici cette semaine": {
        "en": "Songs: {n} species possible here this week", "es": "Cantos: {n} especies posibles aquí esta semana",
        "de": "Gesänge: {n} hier diese Woche mögliche Arten", "pt": "Cantos: {n} espécies possíveis aqui esta semana",
        "it": "Canti: {n} specie possibili qui questa settimana"},
    "Filtre géographique indisponible ({erreur})": {
        "en": "Location filter unavailable ({erreur})", "es": "Filtro geográfico no disponible ({erreur})",
        "de": "Geografischer Filter nicht verfügbar ({erreur})", "pt": "Filtro geográfico indisponível ({erreur})",
        "it": "Filtro geografico non disponibile ({erreur})"},
    "Écoute des chants : micro actif ({freq} Hz)": {
        "en": "Listening: microphone active ({freq} Hz)", "es": "Escucha: micrófono activo ({freq} Hz)",
        "de": "Hören: Mikrofon aktiv ({freq} Hz)", "pt": "Escuta: microfone ativo ({freq} Hz)",
        "it": "Ascolto: microfono attivo ({freq} Hz)"},
    "Écoute des chants impossible : {erreur}": {
        "en": "Cannot listen to songs: {erreur}", "es": "Escucha imposible: {erreur}", "de": "Hören nicht möglich: {erreur}",
        "pt": "Escuta impossível: {erreur}", "it": "Ascolto impossibile: {erreur}"},
    "Ménage : anciens clips effacés : {n}": {"en": "Cleanup: old clips deleted: {n}", "es": "Limpieza: clips antiguos borrados: {n}",
                                             "de": "Aufräumen: alte Clips gelöscht: {n}", "pt": "Limpeza: clipes antigos apagados: {n}",
                                             "it": "Pulizia: vecchie clip eliminate: {n}"},
    "Son de la visite gardé pour apprendre le chant : {espece}": {
        "en": "Visit sound kept to learn the song: {espece}", "es": "Sonido de la visita guardado para aprender el canto: {espece}",
        "de": "Ton des Besuchs behalten, um den Gesang zu lernen: {espece}",
        "pt": "Som da visita guardado para aprender o canto: {espece}",
        "it": "Suono della visita conservato per imparare il canto: {espece}"},
    "Son de la visite non gardé ({erreur})": {"en": "Visit sound not kept ({erreur})", "es": "Sonido de la visita no guardado ({erreur})",
                                              "de": "Ton des Besuchs nicht behalten ({erreur})",
                                              "pt": "Som da visita não guardado ({erreur})",
                                              "it": "Suono della visita non conservato ({erreur})"},
    "Mouvement sans oiseau ({duree} s) : clip effacé": {
        "en": "Motion without a bird ({duree} s): clip deleted", "es": "Movimiento sin ave ({duree} s): clip borrado",
        "de": "Bewegung ohne Vogel ({duree} s): Clip gelöscht", "pt": "Movimento sem ave ({duree} s): clipe apagado",
        "it": "Movimento senza uccello ({duree} s): clip eliminata"},
    "Fin de visite : {espece} ({conf}), {duree} s": {
        "en": "Visit ended: {espece} ({conf}), {duree} s", "es": "Fin de la visita: {espece} ({conf}), {duree} s",
        "de": "Besuch beendet: {espece} ({conf}), {duree} s", "pt": "Fim da visita: {espece} ({conf}), {duree} s",
        "it": "Fine visita: {espece} ({conf}), {duree} s"},
    "Clips interrompus illisibles effacés : {n}": {
        "en": "Unreadable interrupted clips deleted: {n}", "es": "Clips interrumpidos ilegibles borrados: {n}",
        "de": "Unlesbare unterbrochene Clips gelöscht: {n}", "pt": "Clipes interrompidos ilegíveis apagados: {n}",
        "it": "Clip interrotte illeggibili eliminate: {n}"},
    "La source vidéo ne renvoie aucune image : {source} (caméra utilisée par une autre application, ou accès refusé "
    "dans Paramètres › Confidentialité › Caméra)": {
        "en": "The video source returns no image: {source} (camera used by another app, or access denied in "
              "Settings › Privacy › Camera)",
        "es": "La fuente de vídeo no devuelve ninguna imagen: {source} (cámara usada por otra aplicación, o acceso "
              "denegado en Configuración › Privacidad › Cámara)",
        "de": "Die Videoquelle liefert kein Bild: {source} (Kamera von einer anderen App belegt oder Zugriff verweigert "
              "unter Einstellungen › Datenschutz › Kamera)",
        "pt": "A fonte de vídeo não envia nenhuma imagem: {source} (câmera usada por outro aplicativo, ou acesso negado "
              "em Configurações › Privacidade › Câmera)",
        "it": "La sorgente video non restituisce immagini: {source} (fotocamera usata da un'altra app, o accesso negato "
              "in Impostazioni › Privacy › Fotocamera)"},
    "Source ouverte : {largeur}x{hauteur} à {fps} i/s": {
        "en": "Source open: {largeur}x{hauteur} at {fps} fps", "es": "Fuente abierta: {largeur}x{hauteur} a {fps} fps",
        "de": "Quelle geöffnet: {largeur}x{hauteur} mit {fps} B/s", "pt": "Fonte aberta: {largeur}x{hauteur} a {fps} fps",
        "it": "Sorgente aperta: {largeur}x{hauteur} a {fps} fps"},
    "Flux interrompu, nouvelle tentative dans 2 s ...": {
        "en": "Stream interrupted, retrying in 2 s ...", "es": "Flujo interrumpido, nuevo intento en 2 s ...",
        "de": "Stream unterbrochen, neuer Versuch in 2 s ...", "pt": "Fluxo interrompido, nova tentativa em 2 s ...",
        "it": "Flusso interrotto, nuovo tentativo tra 2 s ..."},
    "Mouvement : début d'enregistrement": {"en": "Motion: recording started", "es": "Movimiento: inicio de la grabación",
                                           "de": "Bewegung: Aufnahme gestartet", "pt": "Movimento: início da gravação",
                                           "it": "Movimento: inizio registrazione"},
    # ------------------------------------------------------------ complément des chants
    "{n} espèces locales absentes de BirdNET": {"en": "{n} local species missing from BirdNET",
                                                "es": "{n} especies locales ausentes de BirdNET",
                                                "de": "{n} lokale Arten fehlen in BirdNET",
                                                "pt": "{n} espécies locais ausentes do BirdNET",
                                                "it": "{n} specie locali assenti da BirdNET"},
    "{espece} : {n} enregistrement(s), {f} fenêtres": {
        "en": "{espece}: {n} recording(s), {f} windows", "es": "{espece}: {n} grabación(es), {f} ventanas",
        "de": "{espece}: {n} Aufnahme(n), {f} Fenster", "pt": "{espece}: {n} gravação(ões), {f} janelas",
        "it": "{espece}: {n} registrazione/i, {f} finestre"},
    "Aucun enregistrement trouvé : rien à apprendre": {
        "en": "No recordings found: nothing to learn", "es": "No se encontró ninguna grabación: nada que aprender",
        "de": "Keine Aufnahmen gefunden: nichts zu lernen", "pt": "Nenhuma gravação encontrada: nada a aprender",
        "it": "Nessuna registrazione trovata: niente da imparare"},
    "Évaluation (enregistrements jamais entendus)...": {
        "en": "Evaluating (never-heard recordings)...", "es": "Evaluación (grabaciones nunca oídas)...",
        "de": "Auswertung (nie gehörte Aufnahmen)...", "pt": "Avaliação (gravações nunca ouvidas)...",
        "it": "Valutazione (registrazioni mai sentite)..."},
    "Complément des chants : {n} espèces apprises, seuil {seuil}, fausses alertes {fa} sur {t} fenêtres d'autres "
    "oiseaux et de fond": {
        "en": "Song add-on: {n} species learned, threshold {seuil}, false alarms {fa} over {t} windows of other birds "
              "and background",
        "es": "Complemento de cantos: {n} especies aprendidas, umbral {seuil}, falsas alarmas {fa} en {t} ventanas de "
              "otras aves y de fondo",
        "de": "Gesangsergänzung: {n} Arten gelernt, Schwelle {seuil}, Fehlalarme {fa} bei {t} Fenstern anderer Vögel "
              "und Hintergrund",
        "pt": "Complemento de cantos: {n} espécies aprendidas, limiar {seuil}, falsos alarmes {fa} em {t} janelas de "
              "outras aves e de fundo",
        "it": "Complemento dei canti: {n} specie apprese, soglia {seuil}, falsi allarmi {fa} su {t} finestre di altri "
              "uccelli e di fondo"},
    "  téléchargement impossible ({erreur}) : {url}": {
        "en": "  download failed ({erreur}): {url}", "es": "  descarga imposible ({erreur}): {url}",
        "de": "  Download fehlgeschlagen ({erreur}): {url}", "pt": "  download impossível ({erreur}): {url}",
        "it": "  download impossibile ({erreur}): {url}"},
    "  illisible ({erreur}) : {fichier}": {"en": "  unreadable ({erreur}): {fichier}", "es": "  ilegible ({erreur}): {fichier}",
                                           "de": "  unlesbar ({erreur}): {fichier}", "pt": "  ilegível ({erreur}): {fichier}",
                                           "it": "  illeggibile ({erreur}): {fichier}"},
    "  iNaturalist indisponible ({erreur})": {"en": "  iNaturalist unavailable ({erreur})",
                                              "es": "  iNaturalist no disponible ({erreur})",
                                              "de": "  iNaturalist nicht verfügbar ({erreur})",
                                              "pt": "  iNaturalist indisponível ({erreur})",
                                              "it": "  iNaturalist non disponibile ({erreur})"},
    "  xeno-canto indisponible ({erreur}) : clé valide ?": {
        "en": "  xeno-canto unavailable ({erreur}): valid key?", "es": "  xeno-canto no disponible ({erreur}): ¿clave válida?",
        "de": "  xeno-canto nicht verfügbar ({erreur}): gültiger Schlüssel?",
        "pt": "  xeno-canto indisponível ({erreur}): chave válida?", "it": "  xeno-canto non disponibile ({erreur}): chiave valida?"},
}
