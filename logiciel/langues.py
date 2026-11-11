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
    "Micro de la caméra coupé : activez-le dans l'appli de la caméra": {
        "en": "Camera microphone off: turn it on in the camera's app",
        "es": "Micrófono de la cámara apagado: actívelo en la app de la cámara",
        "de": "Kameramikrofon aus: in der App der Kamera einschalten",
        "pt": "Microfone da câmera desligado: ative-o no app da câmera",
        "it": "Microfono della videocamera spento: attivalo nell'app della videocamera"},
    "Écoute des chants : son de la caméra ({freq} Hz)": {
        "en": "Song listening: camera sound ({freq} Hz)", "es": "Escucha de cantos: sonido de la cámara ({freq} Hz)",
        "de": "Gesangserkennung: Ton der Kamera ({freq} Hz)", "pt": "Escuta de cantos: som da câmera ({freq} Hz)",
        "it": "Ascolto dei canti: audio della videocamera ({freq} Hz)"},
    "Son en {freq} Hz : chants appris désactivés, BirdNET seul": {
        "en": "Sound at {freq} Hz: learned songs disabled, BirdNET only",
        "es": "Sonido a {freq} Hz: cantos aprendidos desactivados, solo BirdNET",
        "de": "Ton mit {freq} Hz: gelernte Gesänge deaktiviert, nur BirdNET",
        "pt": "Som a {freq} Hz: cantos aprendidos desativados, apenas BirdNET",
        "it": "Audio a {freq} Hz: canti appresi disattivati, solo BirdNET"},
    "La caméra n'envoie pas de son : écoute sur le micro du PC": {
        "en": "The camera sends no sound: listening with the PC microphone",
        "es": "La cámara no envía sonido: escucha con el micrófono del PC",
        "de": "Die Kamera sendet keinen Ton: Hören über das PC-Mikrofon",
        "pt": "A câmera não envia som: escuta pelo microfone do PC",
        "it": "La videocamera non invia audio: ascolto con il microfono del PC"},
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
    "L'écoute utilise le micro du PC (ou de la webcam USB) ; avec une caméra IP (rtsp://), le micro de la caméra.": {
        "en": "Smartphone: “IP Webcam” app (Android), address like http://192.168.1.20:8080/video.\n"
              "Camera on the Internet (nest, feeder): paste the address of the YouTube page or of the stream,\n"
              "and set the position to the camera's location. The PC microphone is not used for its visits.\n"
              "Listening uses the PC microphone (or the USB webcam's); with an IP camera (rtsp://), the camera's microphone.",
        "es": "Smartphone: app «IP Webcam» (Android), dirección del tipo http://192.168.1.20:8080/video.\n"
              "Cámara en Internet (nido, comedero): pegue la dirección de la página de YouTube o del flujo,\n"
              "y ajuste la posición al lugar de la cámara. El micrófono del PC no se usa para sus visitas.\n"
              "La escucha usa el micrófono del PC (o de la webcam USB); con una cámara IP (rtsp://), el micrófono de la cámara.",
        "de": "Smartphone: App „IP Webcam“ (Android), Adresse wie http://192.168.1.20:8080/video.\n"
              "Kamera im Internet (Nest, Futterhaus): Adresse der YouTube-Seite oder des Streams einfügen\n"
              "und den Standort auf den Ort der Kamera setzen. Das PC-Mikrofon wird für ihre Besuche nicht verwendet.\n"
              "Zum Hören wird das Mikrofon des PCs (oder der USB-Webcam) verwendet, bei einer IP-Kamera (rtsp://) das Mikrofon der Kamera.",
        "pt": "Smartphone: app “IP Webcam” (Android), endereço do tipo http://192.168.1.20:8080/video.\n"
              "Câmera na Internet (ninho, comedouro): cole o endereço da página do YouTube ou do fluxo,\n"
              "e ajuste a posição para o local da câmera. O microfone do PC não é usado para as suas visitas.\n"
              "A escuta usa o microfone do PC (ou da webcam USB); com uma câmera IP (rtsp://), o microfone da câmera.",
        "it": "Smartphone: app «IP Webcam» (Android), indirizzo come http://192.168.1.20:8080/video.\n"
              "Videocamera su Internet (nido, mangiatoia): incolli l'indirizzo della pagina YouTube o del flusso,\n"
              "e imposti la posizione sul luogo della videocamera. Il microfono del PC non è usato per le sue visite.\n"
              "L'ascolto usa il microfono del PC (o della webcam USB); con una videocamera IP (rtsp://), il microfono della videocamera."},
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
    # ------------------------------------------------------------ statistiques et galerie
    "📊  Statistiques": {"en": "📊  Statistics", "es": "📊  Estadísticas", "de": "📊  Statistik",
                        "pt": "📊  Estatísticas", "it": "📊  Statistiche"},
    "🖼  Galerie": {"en": "🖼  Gallery", "es": "🖼  Galería", "de": "🖼  Galerie", "pt": "🖼  Galeria",
                   "it": "🖼  Galleria"},
    "Statistiques — Becquée": {"en": "Statistics — Becquée", "es": "Estadísticas — Becquée",
                               "de": "Statistik — Becquée", "pt": "Estatísticas — Becquée",
                               "it": "Statistiche — Becquée"},
    "Galerie — Becquée": {"en": "Gallery — Becquée", "es": "Galería — Becquée", "de": "Galerie — Becquée",
                          "pt": "Galeria — Becquée", "it": "Galleria — Becquée"},
    "7 jours": {"en": "7 days", "es": "7 días", "de": "7 Tage", "pt": "7 dias", "it": "7 giorni"},
    "30 jours": {"en": "30 days", "es": "30 días", "de": "30 Tage", "pt": "30 dias", "it": "30 giorni"},
    "Tout": {"en": "All", "es": "Todo", "de": "Alles", "pt": "Tudo", "it": "Tutto"},
    "espèces": {"en": "species", "es": "especies", "de": "Arten", "pt": "espécies", "it": "specie"},
    "espèce la plus fréquente": {"en": "most frequent species", "es": "especie más frecuente",
                                 "de": "häufigste Art", "pt": "espécie mais frequente",
                                 "it": "specie più frequente"},
    "Visites par espèce": {"en": "Visits by species", "es": "Visitas por especie", "de": "Besuche pro Art",
                           "pt": "Visitas por espécie", "it": "Visite per specie"},
    "Visites par heure": {"en": "Visits by hour", "es": "Visitas por hora", "de": "Besuche pro Stunde",
                          "pt": "Visitas por hora", "it": "Visite per ora"},
    "Visites par jour": {"en": "Visits by day", "es": "Visitas por día", "de": "Besuche pro Tag",
                         "pt": "Visitas por dia", "it": "Visite per giorno"},
    "Aucune visite sur cette période": {"en": "No visits in this period", "es": "Ninguna visita en este período",
                                        "de": "Keine Besuche in diesem Zeitraum",
                                        "pt": "Nenhuma visita neste período",
                                        "it": "Nessuna visita in questo periodo"},
    "Aucune photo pour l'instant": {"en": "No photos yet", "es": "Todavía no hay fotos", "de": "Noch keine Fotos",
                                    "pt": "Ainda não há fotos", "it": "Ancora nessuna foto"},
    # ------------------------------------------------------------ caméras IP et fenêtres (repris de Broutille)
    ' ; Mercusys ou Tapo probable : {adresses}': {
        'en': '; probably Mercusys or Tapo: {adresses}',
        'es': '; probablemente Mercusys o Tapo: {adresses}',
        'de': '; wahrscheinlich Mercusys oder Tapo: {adresses}',
        'pt': '; provável Mercusys ou Tapo: {adresses}',
        'it': '; probabile Mercusys o Tapo: {adresses}',
    },
    'Adresse IP de la caméra': {
        'en': 'Camera IP address',
        'es': 'Dirección IP de la cámara',
        'de': 'IP-Adresse der Kamera',
        'pt': 'Endereço IP da câmera',
        'it': 'Indirizzo IP della telecamera',
    },
    'Aperçu après « Tester »': {
        'en': 'Preview after “Test”',
        'es': 'Vista previa tras «Probar»',
        'de': 'Vorschau nach „Testen“',
        'pt': 'Prévia após “Testar”',
        'it': 'Anteprima dopo «Prova»',
    },
    "Arrêtez d'abord la surveillance : la caméra n'accepte que peu de connexions à la fois.": {
        'en': 'Stop monitoring first: the camera only accepts a few connections at a time.',
        'es': 'Detenga primero la vigilancia: la cámara solo acepta pocas conexiones a la vez.',
        'de': 'Beenden Sie zuerst die Überwachung: Die Kamera akzeptiert nur wenige Verbindungen gleichzeitig.',
        'pt': 'Pare o monitoramento primeiro: a câmera aceita poucas conexões ao mesmo tempo.',
        'it': 'Fermate prima la sorveglianza: la telecamera accetta poche connessioni alla volta.',
    },
    "Arrêtez d'abord la surveillance.": {
        'en': 'Stop monitoring first.',
        'es': 'Detenga primero la vigilancia.',
        'de': 'Beenden Sie zuerst die Überwachung.',
        'pt': 'Pare o monitoramento primeiro.',
        'it': 'Fermate prima la sorveglianza.',
    },
    "Aucune caméra au flux ouvert. Appareil(s) TP-Link sans flux vidéo : {adresses} (la caméra si son « compte de la caméra » n'est pas créé, ou une prise, un répéteur…). Vérifiez l'adresse dans l'appli : Paramètres de l'appareil → Infos de l'appareil.": {
        'en': 'No camera with an open stream. TP-Link device(s) without a video stream: {adresses} (the camera if its “camera account” has not been created, or a plug, a repeater…). Check the address in the app: Device Settings → Device Info.',
        'es': 'Ninguna cámara con flujo abierto. Dispositivo(s) TP-Link sin flujo de vídeo: {adresses} (la cámara si su «cuenta de la cámara» no está creada, o un enchufe, un repetidor…). Compruebe la dirección en la app: Ajustes del dispositivo → Información del dispositivo.',
        'de': 'Keine Kamera mit offenem Stream. TP-Link-Gerät(e) ohne Videostream: {adresses} (die Kamera, falls ihr „Kamerakonto“ nicht angelegt ist, oder eine Steckdose, ein Repeater…). Prüfen Sie die Adresse in der App: Geräteeinstellungen → Geräteinfo.',
        'pt': 'Nenhuma câmera com stream aberto. Aparelho(s) TP-Link sem stream de vídeo: {adresses} (a câmera, se a “conta da câmera” não foi criada, ou uma tomada, um repetidor…). Verifique o endereço no app: Configurações do dispositivo → Informações do dispositivo.',
        'it': "Nessuna telecamera con flusso aperto. Dispositivo/i TP-Link senza flusso video: {adresses} (la telecamera se il suo «account della telecamera» non è stato creato, o una presa, un ripetitore…). Verificate l'indirizzo nell'app: Impostazioni dispositivo → Info dispositivo.",
    },
    "Aucune caméra trouvée : vérifiez qu'elle est sur le même Wi-Fi, ou lisez son adresse IP dans l'appli (Paramètres de l'appareil → Infos de l'appareil).": {
        'en': 'No camera found: check that it is on the same Wi-Fi, or read its IP address in the app (Device Settings → Device Info).',
        'es': 'No se encontró ninguna cámara: compruebe que está en la misma Wi-Fi, o lea su dirección IP en la app (Ajustes del dispositivo → Información del dispositivo).',
        'de': 'Keine Kamera gefunden: Prüfen Sie, ob sie im selben WLAN ist, oder lesen Sie ihre IP-Adresse in der App ab (Geräteeinstellungen → Geräteinfo).',
        'pt': 'Nenhuma câmera encontrada: verifique se ela está no mesmo Wi-Fi, ou veja o endereço IP no app (Configurações do dispositivo → Informações do dispositivo).',
        'it': "Nessuna telecamera trovata: verificate che sia sullo stesso Wi-Fi, o leggete il suo indirizzo IP nell'app (Impostazioni dispositivo → Info dispositivo).",
    },
    'Aucune image de : {source}': {
        'en': 'No image from: {source}',
        'es': 'Ninguna imagen de: {source}',
        'de': 'Kein Bild von: {source}',
        'pt': 'Nenhuma imagem de: {source}',
        'it': 'Nessuna immagine da: {source}',
    },
    'Autre caméra RTSP': {
        'en': 'Other RTSP camera',
        'es': 'Otra cámara RTSP',
        'de': 'Andere RTSP-Kamera',
        'pt': 'Outra câmera RTSP',
        'it': 'Altra telecamera RTSP',
    },
    'Cadrage enregistré pour cette source': {
        'en': 'Crop saved for this source',
        'es': 'Encuadre guardado para esta fuente',
        'de': 'Zuschnitt für diese Quelle gespeichert',
        'pt': 'Enquadramento salvo para esta fonte',
        'it': 'Inquadratura salvata per questa sorgente',
    },
    'Cadrer': {
        'en': 'Crop',
        'es': 'Encuadrar',
        'de': 'Zuschneiden',
        'pt': 'Enquadrar',
        'it': 'Inquadra',
    },
    'Cadrer : tracez la zone de la mangeoire à la souris': {
        'en': 'Crop: draw the feeder area with the mouse',
        'es': 'Encuadrar: trace la zona del comedero con el ratón',
        'de': 'Zuschneiden: Ziehen Sie den Bereich der Futterstelle mit der Maus',
        'pt': 'Enquadrar: desenhe a área do comedouro com o mouse',
        'it': 'Inquadra: tracciate la zona della mangiatoia con il mouse',
    },
    'Caméra IP': {
        'en': 'IP camera',
        'es': 'Cámara IP',
        'de': 'IP-Kamera',
        'pt': 'Câmera IP',
        'it': 'Telecamera IP',
    },
    'Caméra IP (Mercusys, Tapo…)': {
        'en': 'IP camera (Mercusys, Tapo…)',
        'es': 'Cámara IP (Mercusys, Tapo…)',
        'de': 'IP-Kamera (Mercusys, Tapo…)',
        'pt': 'Câmera IP (Mercusys, Tapo…)',
        'it': 'Telecamera IP (Mercusys, Tapo…)',
    },
    'Caméra IP : {adresse}': {
        'en': 'IP camera: {adresse}',
        'es': 'Cámara IP: {adresse}',
        'de': 'IP-Kamera: {adresse}',
        'pt': 'Câmera IP: {adresse}',
        'it': 'Telecamera IP: {adresse}',
    },
    'Chemin du flux et port': {
        'en': 'Stream path and port',
        'es': 'Ruta del flujo y puerto',
        'de': 'Stream-Pfad und Port',
        'pt': 'Caminho do stream e porta',
        'it': 'Percorso del flusso e porta',
    },
    'Chercher sur le Wi-Fi': {
        'en': 'Search Wi-Fi',
        'es': 'Buscar en la Wi-Fi',
        'de': 'Im WLAN suchen',
        'pt': 'Procurar no Wi-Fi',
        'it': 'Cerca sul Wi-Fi',
    },
    'Choisir': {
        'en': 'Choose',
        'es': 'Elegir',
        'de': 'Wählen',
        'pt': 'Escolher',
        'it': 'Scegli',
    },
    'Connexion à la caméra…': {
        'en': 'Connecting to the camera…',
        'es': 'Conectando con la cámara…',
        'de': 'Verbindung zur Kamera…',
        'pt': 'Conectando à câmera…',
        'it': 'Connessione alla telecamera…',
    },
    'Fenêtre': {
        'en': 'Window',
        'es': 'Ventana',
        'de': 'Fenster',
        'pt': 'Janela',
        'it': 'Finestra',
    },
    'Fenêtre : {titre}': {
        'en': 'Window: {titre}',
        'es': 'Ventana: {titre}',
        'de': 'Fenster: {titre}',
        'pt': 'Janela: {titre}',
        'it': 'Finestra: {titre}',
    },
    'Filmer une fenêtre ouverte': {
        'en': 'Film an open window',
        'es': 'Grabar una ventana abierta',
        'de': 'Ein offenes Fenster filmen',
        'pt': 'Filmar uma janela aberta',
        'it': 'Filmare una finestra aperta',
    },
    'Haute qualité (stream1)': {
        'en': 'High quality (stream1)',
        'es': 'Alta calidad (stream1)',
        'de': 'Hohe Qualität (stream1)',
        'pt': 'Alta qualidade (stream1)',
        'it': 'Alta qualità (stream1)',
    },
    'Identifiant (compte de la caméra)': {
        'en': 'Username (camera account)',
        'es': 'Usuario (cuenta de la cámara)',
        'de': 'Benutzername (Kamerakonto)',
        'pt': 'Usuário (conta da câmera)',
        'it': 'Nome utente (account della telecamera)',
    },
    'Image': {
        'en': 'Image',
        'es': 'Imagen',
        'de': 'Bild',
        'pt': 'Imagem',
        'it': 'Immagine',
    },
    'Image reçue : {largeur}×{hauteur}. Cliquez sur « Utiliser cette caméra ».': {
        'en': 'Image received: {largeur}×{hauteur}. Click “Use this camera”.',
        'es': 'Imagen recibida: {largeur}×{hauteur}. Haga clic en «Usar esta cámara».',
        'de': 'Bild empfangen: {largeur}×{hauteur}. Klicken Sie auf „Diese Kamera verwenden“.',
        'pt': 'Imagem recebida: {largeur}×{hauteur}. Clique em “Usar esta câmera”.',
        'it': 'Immagine ricevuta: {largeur}×{hauteur}. Cliccate su «Usa questa telecamera».',
    },
    'Impossible : {erreur}': {
        'en': 'Not possible: {erreur}',
        'es': 'Imposible: {erreur}',
        'de': 'Nicht möglich: {erreur}',
        'pt': 'Impossível: {erreur}',
        'it': 'Impossibile: {erreur}',
    },
    'La caméra ne connaît pas ce chemin de flux : choisissez la marque Mercusys, ou vérifiez le chemin (stream1 / stream2).': {
        'en': 'The camera does not know this stream path: choose the Mercusys brand, or check the path (stream1 / stream2).',
        'es': 'La cámara no reconoce esta ruta de flujo: elija la marca Mercusys o compruebe la ruta (stream1 / stream2).',
        'de': 'Die Kamera kennt diesen Stream-Pfad nicht: Wählen Sie die Marke Mercusys oder prüfen Sie den Pfad (stream1 / stream2).',
        'pt': 'A câmera não conhece este caminho de stream: escolha a marca Mercusys ou verifique o caminho (stream1 / stream2).',
        'it': 'La telecamera non conosce questo percorso di flusso: scegliete la marca Mercusys o verificate il percorso (stream1 / stream2).',
    },
    "La caméra refuse cet identifiant et ce mot de passe. Une adresse e-mail est celle du compte Mercusys : il faut le « compte de la caméra », créé à part dans l'appli (Paramètres avancés → Compte de la caméra).": {
        'en': 'The camera rejects this username and password. An e-mail address belongs to the Mercusys account: you need the “camera account”, created separately in the app (Advanced Settings → Camera Account).',
        'es': 'La cámara rechaza este usuario y esta contraseña. Una dirección de correo es la de la cuenta Mercusys: hace falta la «cuenta de la cámara», creada aparte en la app (Ajustes avanzados → Cuenta de la cámara).',
        'de': 'Die Kamera lehnt diesen Benutzernamen und dieses Passwort ab. Eine E-Mail-Adresse gehört zum Mercusys-Konto: Sie brauchen das „Kamerakonto“, das separat in der App angelegt wird (Erweiterte Einstellungen → Kamerakonto).',
        'pt': 'A câmera recusa este usuário e senha. Um endereço de e-mail é o da conta Mercusys: é preciso a “conta da câmera”, criada à parte no app (Configurações avançadas → Conta da câmera).',
        'it': "La telecamera rifiuta questo nome utente e questa password. Un indirizzo e-mail è quello dell'account Mercusys: serve l'«account della telecamera», creato a parte nell'app (Impostazioni avanzate → Account della telecamera).",
    },
    "La caméra refuse cet identifiant et ce mot de passe. Utilisez ceux du « compte de la caméra » (Paramètres avancés → Compte de la caméra dans l'appli), en respectant majuscules et minuscules.": {
        'en': 'The camera rejects this username and password. Use those of the “camera account” (Advanced Settings → Camera Account in the app), respecting upper and lower case.',
        'es': 'La cámara rechaza este usuario y esta contraseña. Use los de la «cuenta de la cámara» (Ajustes avanzados → Cuenta de la cámara en la app), respetando mayúsculas y minúsculas.',
        'de': 'Die Kamera lehnt diesen Benutzernamen und dieses Passwort ab. Verwenden Sie die des „Kamerakontos“ (Erweiterte Einstellungen → Kamerakonto in der App) und achten Sie auf Groß- und Kleinschreibung.',
        'pt': 'A câmera recusa este usuário e senha. Use os da “conta da câmera” (Configurações avançadas → Conta da câmera no app), respeitando maiúsculas e minúsculas.',
        'it': "La telecamera rifiuta questo nome utente e questa password. Usate quelli dell'«account della telecamera» (Impostazioni avanzate → Account della telecamera nell'app), rispettando maiuscole e minuscole.",
    },
    'Lecture de la source…': {
        'en': 'Reading the source…',
        'es': 'Leyendo la fuente…',
        'de': 'Quelle wird gelesen…',
        'pt': 'Lendo a fonte…',
        'it': 'Lettura della sorgente…',
    },
    'Légère (stream2)': {
        'en': 'Light (stream2)',
        'es': 'Ligera (stream2)',
        'de': 'Leicht (stream2)',
        'pt': 'Leve (stream2)',
        'it': 'Leggera (stream2)',
    },
    'Marque': {
        'en': 'Brand',
        'es': 'Marca',
        'de': 'Marke',
        'pt': 'Marca',
        'it': 'Marca',
    },
    'Mot de passe': {
        'en': 'Password',
        'es': 'Contraseña',
        'de': 'Passwort',
        'pt': 'Senha',
        'it': 'Password',
    },
    "Pas d'image : vérifiez l'adresse IP et le compte de la caméra (identifiant et mot de passe créés dans l'appli, pas ceux du compte Mercusys).": {
        'en': 'No image: check the IP address and the camera account (username and password created in the app, not those of the Mercusys account).',
        'es': 'Sin imagen: compruebe la dirección IP y la cuenta de la cámara (usuario y contraseña creados en la app, no los de la cuenta Mercusys).',
        'de': 'Kein Bild: Prüfen Sie die IP-Adresse und das Kamerakonto (Benutzername und Passwort aus der App, nicht die des Mercusys-Kontos).',
        'pt': 'Sem imagem: verifique o endereço IP e a conta da câmera (usuário e senha criados no app, não os da conta Mercusys).',
        'it': "Nessuna immagine: verificate l'indirizzo IP e l'account della telecamera (nome utente e password creati nell'app, non quelli dell'account Mercusys).",
    },
    'Recherche des caméras sur le réseau (une dizaine de secondes)…': {
        'en': 'Searching for cameras on the network (about ten seconds)…',
        'es': 'Buscando cámaras en la red (unos diez segundos)…',
        'de': 'Suche nach Kameras im Netzwerk (etwa zehn Sekunden)…',
        'pt': 'Procurando câmeras na rede (uns dez segundos)…',
        'it': 'Ricerca delle telecamere in rete (una decina di secondi)…',
    },
    'Tester': {
        'en': 'Test',
        'es': 'Probar',
        'de': 'Testen',
        'pt': 'Testar',
        'it': 'Prova',
    },
    "Toute l'image": {
        'en': 'Whole image',
        'es': 'Toda la imagen',
        'de': 'Ganzes Bild',
        'pt': 'Imagem inteira',
        'it': "Tutta l'immagine",
    },
    'Utiliser cette caméra': {
        'en': 'Use this camera',
        'es': 'Usar esta cámara',
        'de': 'Diese Kamera verwenden',
        'pt': 'Usar esta câmera',
        'it': 'Usa questa telecamera',
    },
    'Valider la zone': {
        'en': 'Confirm area',
        'es': 'Validar la zona',
        'de': 'Bereich bestätigen',
        'pt': 'Confirmar a área',
        'it': 'Conferma la zona',
    },
    'Zone trop petite.': {
        'en': 'Area too small.',
        'es': 'Zona demasiado pequeña.',
        'de': 'Bereich zu klein.',
        'pt': 'Área pequena demais.',
        'it': 'Zona troppo piccola.',
    },
    'port illisible': {
        'en': 'unreadable port',
        'es': 'puerto ilegible',
        'de': 'Port unlesbar',
        'pt': 'porta ilegível',
        'it': 'porta illeggibile',
    },
    "{adresse} ne répond pas sur le port vidéo ({port}) : le « compte de la caméra » n'est pas encore créé, ou ce n'est pas l'adresse de la caméra (vérifiez-la dans l'appli : Paramètres de l'appareil → Infos de l'appareil).": {
        'en': "{adresse} does not respond on the video port ({port}): the “camera account” has not been created yet, or this is not the camera's address (check it in the app: Device Settings → Device Info).",
        'es': '{adresse} no responde en el puerto de vídeo ({port}): la «cuenta de la cámara» aún no está creada, o no es la dirección de la cámara (compruébela en la app: Ajustes del dispositivo → Información del dispositivo).',
        'de': '{adresse} antwortet nicht auf dem Videoport ({port}): Das „Kamerakonto“ ist noch nicht angelegt, oder das ist nicht die Adresse der Kamera (prüfen Sie sie in der App: Geräteeinstellungen → Geräteinfo).',
        'pt': '{adresse} não responde na porta de vídeo ({port}): a “conta da câmera” ainda não foi criada, ou este não é o endereço da câmera (verifique no app: Configurações do dispositivo → Informações do dispositivo).',
        'it': "{adresse} non risponde sulla porta video ({port}): l'«account della telecamera» non è ancora stato creato, o non è l'indirizzo della telecamera (verificatelo nell'app: Impostazioni dispositivo → Info dispositivo).",
    },
    'Caméra choisie : {camera}': {
        'en': 'Camera selected: {camera}',
        'es': 'Cámara elegida: {camera}',
        'de': 'Kamera gewählt: {camera}',
        'pt': 'Câmera escolhida: {camera}',
        'it': 'Videocamera scelta: {camera}',
    },
    'Caméras trouvées : {n}': {
        'en': 'Cameras found: {n}',
        'es': 'Cámaras encontradas: {n}',
        'de': 'Gefundene Kameras: {n}',
        'pt': 'Câmeras encontradas: {n}',
        'it': 'Videocamere trovate: {n}',
    },
    "Dans l'appli Mercusys, créez d'abord le « compte de la caméra » (différent de votre compte Mercusys) :\nAccueil → carte de la caméra → Paramètres de l'appareil → Paramètres avancés → Compte de la caméra.\nPour que l'adresse ne change pas, réservez-la dans votre box (bail DHCP fixe).": {
        'en': 'In the Mercusys app, first create the “camera account” (different from your Mercusys account):\nHome → camera card → Device Settings → Advanced Settings → Camera Account.\nSo that the address does not change, reserve it in your router (fixed DHCP lease).',
        'es': 'En la app Mercusys, cree primero la «cuenta de la cámara» (distinta de su cuenta Mercusys):\nInicio → tarjeta de la cámara → Ajustes del dispositivo → Ajustes avanzados → Cuenta de la cámara.\nPara que la dirección no cambie, resérvela en su router (concesión DHCP fija).',
        'de': 'Legen Sie in der Mercusys-App zuerst das „Kamerakonto“ an (nicht Ihr Mercusys-Konto):\nStartseite → Kamerakarte → Geräteeinstellungen → Erweiterte Einstellungen → Kamerakonto.\nDamit sich die Adresse nicht ändert, reservieren Sie sie im Router (feste DHCP-Zuweisung).',
        'pt': 'No app Mercusys, crie primeiro a “conta da câmera” (diferente da sua conta Mercusys):\nInício → cartão da câmera → Configurações do dispositivo → Configurações avançadas → Conta da câmera.\nPara que o endereço não mude, reserve-o no seu roteador (concessão DHCP fixa).',
        'it': "Nell'app Mercusys, crei prima l'«account della videocamera» (diverso dal suo account Mercusys):\nHome → scheda della videocamera → Impostazioni dispositivo → Impostazioni avanzate → Account videocamera.\nPerché l'indirizzo non cambi, lo riservi nel router (lease DHCP fisso).",
    },
    'Fenêtre choisie : cliquez sur « Démarrer » (⛶ Cadrer si elle montre plusieurs caméras).': {
        'en': 'Window selected: click “Start” (⛶ Crop if it shows several cameras).',
        'es': 'Ventana elegida: pulse «Iniciar» (⛶ Encuadrar si muestra varias cámaras).',
        'de': 'Fenster gewählt: auf „Starten“ klicken (⛶ Zuschneiden, wenn es mehrere Kameras zeigt).',
        'pt': 'Janela escolhida: clique em “Iniciar” (⛶ Enquadrar se ela mostrar várias câmeras).',
        'it': 'Finestra scelta: clicchi su «Avvia» (⛶ Inquadra se mostra più videocamere).',
    },
    "La fenêtre doit rester ouverte, pas réduite.\nElle peut être cachée par d'autres : Becquée y trouve seul la vidéo.": {
        'en': 'The window must stay open, not minimised.\nIt can be hidden behind others: Becquée finds the video in it by itself.',
        'es': 'La ventana debe quedar abierta, no minimizada.\nPuede estar tapada por otras: Becquée encuentra el vídeo por sí solo.',
        'de': 'Das Fenster muss offen bleiben, nicht minimiert.\nEs darf von anderen verdeckt sein: Becquée findet das Video darin selbst.',
        'pt': 'A janela deve ficar aberta, não minimizada.\nEla pode ficar escondida atrás de outras: o Becquée encontra o vídeo sozinho.',
        'it': 'La finestra deve restare aperta, non ridotta a icona.\nPuò essere nascosta da altre: Becquée vi trova da solo il video.',
    },
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
