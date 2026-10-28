package io.github.oli97430.becquee

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.graphics.BitmapFactory
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as itemsGrille
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.Locale

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // test automatique : adb shell am start -n <appli>/.MainActivity --es video <chemin du fichier>
        // seulement une vidéo déposée dans le dossier de l'appli (l'activité est accessible aux autres applis)
        val dossierTest = (getExternalFilesDir(null) ?: filesDir).canonicalFile
        intent.getStringExtra("video")?.let { File(it).canonicalFile }?.takeIf { it.isFile && it.parentFile == dossierTest }?.let { video ->
            intent.getStringExtra("latitude")?.toDoubleOrNull()?.takeIf { it in -90.0..90.0 }?.let { Reglages(this).latitude = it }
            intent.getStringExtra("longitude")?.toDoubleOrNull()?.takeIf { it in -180.0..180.0 }?.let { Reglages(this).longitude = it }
            // mesures de vitesse : --es acceleration cpu|xnnpack|nnapi --es fils 4
            intent.getStringExtra("acceleration")?.takeIf { it in listOf("cpu", "xnnpack", "nnapi") }?.let { Reglages(this).acceleration = it }
            intent.getStringExtra("fils")?.toIntOrNull()?.takeIf { it in 1..8 }?.let { Reglages(this).fils = it }
            val mode = if (intent.getStringExtra("direct") == "1") SurveillanceService.SIMULATION else SurveillanceService.FICHIER
            SurveillanceService.lancer(this, mode, Uri.fromFile(video))
        }
        setContent {
            MaterialTheme(colorScheme = Couleurs.theme) { Ecran() }
        }
    }
}

/** Couleurs de l'appli Windows (thème sombre « nuit de mangeoire »). */
private object Couleurs {
    val fond = Color(0xFF0F1419)
    val carte = Color(0xFF17202A)
    val bord = Color(0xFF263241)
    val texte = Color(0xFFE6EDF3)
    val discret = Color(0xFF8B98A5)
    val vert = Color(0xFF3FB950)
    val rouge = Color(0xFFF85149)
    val bleu = Color(0xFF58A6FF)
    val ambre = Color(0xFFD29922)
    val theme = darkColorScheme(
        primary = vert, onPrimary = Color(0xFF0B1F10), secondary = bleu, tertiary = ambre, error = rouge,
        background = fond, onBackground = texte, surface = fond, onSurface = texte, surfaceVariant = carte,
        onSurfaceVariant = discret, surfaceContainer = carte, surfaceContainerHigh = carte, surfaceContainerHighest = bord,
        surfaceContainerLow = carte, outline = bord, outlineVariant = bord, secondaryContainer = Color(0xFF1F3A5F),
        onSecondaryContainer = texte,
    )
}

@Composable
private fun EnTete() {
    val marche by Etat.marche.collectAsStateWithLifecycle()
    val vue by Etat.vue.collectAsStateWithLifecycle()
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
        Image(androidx.compose.ui.res.painterResource(R.drawable.logo_becquee), null, Modifier.size(44.dp))
        Column(Modifier.weight(1f).padding(start = 12.dp)) {
            Text(stringResource(R.string.app_name), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text(stringResource(R.string.slogan), style = MaterialTheme.typography.bodySmall, color = Couleurs.discret)
        }
        // pastille d'état, comme sur le PC : vert = surveillance, rouge = enregistrement
        val couleur = when {
            vue.enregistrement && marche != null -> Couleurs.rouge
            marche != null -> Couleurs.vert
            else -> Couleurs.discret
        }
        Canvas(Modifier.size(14.dp)) { drawCircle(couleur) }
    }
}

@Composable
private fun Ecran() {
    var onglet by rememberSaveable { mutableIntStateOf(0) }
    Scaffold(containerColor = Couleurs.fond, topBar = { Box(Modifier.statusBarsPadding()) { EnTete() } }, bottomBar = {
        NavigationBar(containerColor = Couleurs.carte) {
            NavigationBarItem(onglet == 0, { onglet = 0 }, { Icon(Icons.Default.Videocam, null) }, label = { Text(stringResource(R.string.onglet_direct)) })
            NavigationBarItem(onglet == 1, { onglet = 1 }, { Icon(Icons.AutoMirrored.Filled.List, null) }, label = { Text(stringResource(R.string.onglet_visites)) })
            NavigationBarItem(onglet == 2, { onglet = 2 }, { Icon(Icons.Default.PhotoLibrary, null) }, label = { Text(stringResource(R.string.onglet_galerie)) })
            NavigationBarItem(onglet == 3, { onglet = 3 }, { Icon(Icons.Default.BarChart, null) }, label = { Text(stringResource(R.string.onglet_stats)) })
            NavigationBarItem(onglet == 4, { onglet = 4 }, { Icon(Icons.Default.Settings, null) }, label = { Text(stringResource(R.string.onglet_reglages)) })
        }
    }) { marges ->
        Box(Modifier.padding(marges).fillMaxSize()) {
            when (onglet) {
                0 -> Direct()
                1 -> Visites()
                2 -> Galerie()
                3 -> Statistiques()
                else -> ReglagesEcran()
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Direct() {
    val context = LocalContext.current
    val image by Etat.image.collectAsStateWithLifecycle()
    val vue by Etat.vue.collectAsStateWithLifecycle()
    val marche by Etat.marche.collectAsStateWithLifecycle()
    val messages by Etat.messages.collectAsStateWithLifecycle()
    val choisirVideo = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) SurveillanceService.lancer(context, SurveillanceService.FICHIER, uri)
    }
    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { r ->
        if (r[Manifest.permission.CAMERA] == true) SurveillanceService.lancer(context, SurveillanceService.CAMERA)
    }
    val paysage = LocalConfiguration.current.orientation == Configuration.ORIENTATION_LANDSCAPE
    val imageDirect = @Composable { m: Modifier ->
        Box(m.background(Color(0xFF05080B)), contentAlignment = Alignment.Center) {
            val b = image
            if (b == null) Text(stringResource(R.string.aucune_image), Modifier.padding(16.dp))
            else {
                Image(b.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
                Canvas(Modifier.fillMaxSize()) {
                    // mêmes repères que sur le PC : orange = mouvement, vert = oiseau
                    val e = minOf(size.width / b.width, size.height / b.height)
                    val ox = (size.width - b.width * e) / 2
                    val oy = (size.height - b.height * e) / 2
                    fun cadre(r: Boite, c: Color) = drawRect(c, Offset(ox + r.x * e, oy + r.y * e), Size(r.l * e, r.h * e), style = Stroke(3f))
                    vue.boite?.let { cadre(it, Color(0xFFFFA000)) }
                    vue.oiseaux.forEach { cadre(it, Color(0xFF00C853)) }
                    if (vue.enregistrement) drawCircle(Color.Red, 12f, Offset(ox + 24f, oy + 24f))
                }
            }
        }
    }
    val commandes = @Composable { m: Modifier ->
        Column(m) {
            Text(buildString {
                if (marche != null) append(String.format(Locale.getDefault(), "%.0f i/s", vue.fps))
                if (vue.enregistrement) append("  ●  " + String.format(Locale.getDefault(), "%.0f s", vue.duree))
                if (vue.etiquette.isNotEmpty()) append("  ${vue.etiquette}")
            }, fontWeight = FontWeight.Bold)
            // les modèles attendent une image en largeur : la mangeoire se filme téléphone couché
            if (marche == SurveillanceService.CAMERA && !paysage)
                Text(stringResource(R.string.tenir_paysage), color = Couleurs.ambre, style = MaterialTheme.typography.bodySmall)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
                if (marche == null) {
                    Button({
                        val demandees = mutableListOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
                        if (Build.VERSION.SDK_INT >= 33) demandees.add(Manifest.permission.POST_NOTIFICATIONS)
                        permissions.launch(demandees.toTypedArray())
                    }) { Text(stringResource(R.string.demarrer)) }
                    OutlinedButton({ choisirVideo.launch(arrayOf("video/*")) }) { Text(stringResource(R.string.analyser_video)) }
                } else Button({ SurveillanceService.lancer(context, SurveillanceService.ARRETER) }) { Text(stringResource(R.string.arreter)) }
            }
            Column(Modifier.heightIn(max = 140.dp).verticalScroll(rememberScrollState())) {
                messages.takeLast(8).reversed().forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
            }
        }
    }
    if (paysage) Row(Modifier.fillMaxSize().padding(12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        imageDirect(Modifier.weight(1f).fillMaxHeight())
        commandes(Modifier.width(260.dp).verticalScroll(rememberScrollState()))
    } else Column(Modifier.fillMaxSize().padding(12.dp)) {
        imageDirect(Modifier.fillMaxWidth().weight(1f))
        commandes(Modifier.fillMaxWidth())
    }
}

@Composable
private fun nomAffiche(espece: String) = when (espece) {
    INCONNU -> stringResource(R.string.inconnu)
    PAS_UN_OISEAU -> stringResource(R.string.pas_un_oiseau)
    else -> espece
}

@Composable
private fun Visites() {
    val context = LocalContext.current
    val version by Etat.versionJournal.collectAsStateWithLifecycle()
    val dossier = remember { dossierVisites(context) }
    var visites by remember { mutableStateOf(emptyList<Map<String, String>>()) }
    var aCorriger by remember { mutableStateOf<Map<String, String>?>(null) }
    LaunchedEffect(version) { visites = withContext(Dispatchers.IO) { Journal(dossier).lire().reversed() } }
    if (visites.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text(stringResource(R.string.aucune_visite)) }
        return
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item { Text(stringResource(R.string.nb_visites, visites.size, visites.map { it["espece"] }.filter { it != INCONNU }.toSet().size),
            style = MaterialTheme.typography.titleMedium) }
        items(visites, key = { it["video"].orEmpty() }) { v ->
            Card(colors = CardDefaults.cardColors(containerColor = Couleurs.carte, contentColor = Couleurs.texte), modifier = Modifier.fillMaxWidth().clickable { ouvrirClip(context, File(dossier, v["video"].orEmpty())) }) {
                Row(Modifier.padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Miniature(File(dossier, v["photo"].orEmpty()))
                    Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                        Text(nomAffiche(v["espece"].orEmpty()), fontWeight = FontWeight.Bold)
                        Text("${v["date"]}  ${v["heure"]}  ·  ${v["duree_s"]} s  ·  ${((v["confiance"]?.toFloatOrNull() ?: 0f) * 100).toInt()} %" +
                                if (v["corrige"] == "1") "  ✓" else "", style = MaterialTheme.typography.bodySmall)
                    }
                    TextButton({ aCorriger = v }) { Text(stringResource(R.string.corriger)) }
                }
            }
        }
    }
    aCorriger?.let { v -> DialogueCorrection(v, onFin = { aCorriger = null }) }
}

@Composable
private fun Miniature(photo: File, m: Modifier = Modifier.size(96.dp, 72.dp), echantillon: Int = 4) {
    val b by produceState<android.graphics.Bitmap?>(null, photo) {
        value = withContext(Dispatchers.IO) {
            if (!photo.isFile) null else BitmapFactory.decodeFile(photo.path, BitmapFactory.Options().apply { inSampleSize = echantillon })
        }
    }
    Box(m) {
        b?.let { Image(it.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop) }
    }
}

private fun ouvrirClip(context: android.content.Context, f: File) {
    if (!f.exists()) return
    val uri = FileProvider.getUriForFile(context, context.packageName + ".fichiers", f)
    context.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, "video/mp4").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
}

@Composable
private fun DialogueCorrection(visite: Map<String, String>, onFin: () -> Unit) {
    val context = LocalContext.current
    val portee = rememberCoroutineScope()
    var recherche by remember { mutableStateOf("") }
    var especes by remember { mutableStateOf(emptyList<String>()) }
    LaunchedEffect(Unit) {
        especes = withContext(Dispatchers.IO) {
            val r = Reglages(context)
            Etat.reconnaisseur?.noms?.takeIf { it.isNotEmpty() }
                ?: Especes.locales(context, r.latitude, r.longitude) {}.map { it.nom }
        }
    }
    val pasOiseau = stringResource(R.string.pas_un_oiseau)
    AlertDialog(onDismissRequest = onFin, confirmButton = {}, dismissButton = { TextButton(onFin) { Text(stringResource(R.string.annuler)) } },
        title = { Text(stringResource(R.string.corriger_titre)) },
        text = {
            Column {
                OutlinedTextField(recherche, { recherche = it }, singleLine = true, label = { Text(stringResource(R.string.rechercher)) })
                val cle = cleEspece(recherche)
                val liste = (listOf(PAS_UN_OISEAU) + especes.filter { it != PAS_UN_OISEAU }).filter { cle.isEmpty() || cleEspece(it).contains(cle) }
                    .let { if (recherche.isNotBlank() && it.none { e -> cleEspece(e) == cle }) it + recherche.trim() else it }
                LazyColumn(Modifier.heightIn(max = 360.dp)) {
                    items(liste) { e ->
                        Text(if (e == PAS_UN_OISEAU) pasOiseau else e, Modifier.fillMaxWidth().clickable {
                            portee.launch {
                                withContext(Dispatchers.IO) {
                                    Journal(dossierVisites(context)).corriger(visite["video"].orEmpty(), e)
                                    Etat.reconnaisseur?.apprendre()
                                }
                                Etat.versionJournal.value++
                                onFin()
                            }
                        }.padding(vertical = 10.dp))
                    }
                }
            }
        })
}

@SuppressLint("MissingPermission")
@Composable
private fun ReglagesEcran() {
    val context = LocalContext.current
    val r = remember { Reglages(context) }
    var latitude by remember { mutableStateOf(r.latitude?.toString().orEmpty()) }
    var longitude by remember { mutableStateOf(r.longitude?.toString().orEmpty()) }
    var seuil by remember { mutableFloatStateOf(r.seuil) }
    var surface by remember { mutableFloatStateOf(r.surface) }
    var filtre by remember { mutableStateOf(r.filtreOiseaux) }
    var son by remember { mutableStateOf(r.son) }
    var menageJours by remember { mutableIntStateOf(r.menageJours) }
    var menageGo by remember { mutableFloatStateOf(r.menageGo) }
    fun lirePosition() {
        val lm = context.getSystemService(LocationManager::class.java)
        val p = lm.getProviders(true).mapNotNull { lm.getLastKnownLocation(it) }.maxByOrNull { it.time } ?: return
        latitude = String.format(Locale.US, "%.3f", p.latitude); longitude = String.format(Locale.US, "%.3f", p.longitude)
        r.latitude = latitude.toDouble(); r.longitude = longitude.toDouble()
    }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { if (it) lirePosition() }
    Column(Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.position_titre), style = MaterialTheme.typography.titleMedium)
        Text(stringResource(R.string.position_aide), style = MaterialTheme.typography.bodySmall)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(latitude, { latitude = it; r.latitude = it.toDoubleOrNull() }, Modifier.weight(1f), label = { Text("Latitude") }, singleLine = true)
            OutlinedTextField(longitude, { longitude = it; r.longitude = it.toDoubleOrNull() }, Modifier.weight(1f), label = { Text("Longitude") }, singleLine = true)
        }
        OutlinedButton({
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED) lirePosition()
            else permission.launch(Manifest.permission.ACCESS_COARSE_LOCATION)
        }) { Text(stringResource(R.string.ma_position)) }
        HorizontalDivider()
        Text(stringResource(R.string.seuil, (seuil * 100).toInt()))
        Slider(seuil, { seuil = it; r.seuil = it; Etat.surveillance?.seuil = it }, valueRange = 0.3f..0.99f)
        Text(stringResource(R.string.surface, String.format(Locale.getDefault(), "%.1f", surface * 100)))
        Slider(surface, { surface = it; r.surface = it; Etat.surveillance?.surface = it }, valueRange = 0.002f..0.1f)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Switch(filtre, { filtre = it; r.filtreOiseaux = it; Etat.surveillance?.filtreOiseaux = it })
            Text(stringResource(R.string.filtre_oiseaux), Modifier.padding(start = 12.dp))
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Switch(son, { son = it; r.son = it })
            Text(stringResource(R.string.son_clips), Modifier.padding(start = 12.dp))
        }
        HorizontalDivider()
        Text(stringResource(R.string.menage_titre), style = MaterialTheme.typography.titleMedium)
        Text(stringResource(R.string.menage_aide), style = MaterialTheme.typography.bodySmall)
        Text(stringResource(R.string.menage_jours, menageJours))
        Slider(menageJours.toFloat(), { menageJours = it.toInt(); r.menageJours = menageJours }, valueRange = 7f..365f)
        Text(stringResource(R.string.menage_go, menageGo.toInt()))
        Slider(menageGo, { menageGo = it.toInt().toFloat(); r.menageGo = menageGo }, valueRange = 1f..50f)
        HorizontalDivider()
        Text(stringResource(R.string.dossier, dossierVisites(context).path), style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun Galerie() {
    val context = LocalContext.current
    val version by Etat.versionJournal.collectAsStateWithLifecycle()
    val dossier = remember { dossierVisites(context) }
    var photos by remember { mutableStateOf(emptyList<Pair<String, org.json.JSONObject>>()) }
    LaunchedEffect(version) {
        photos = withContext(Dispatchers.IO) {
            Rangement.construireGalerie(dossier)
            val index = Rangement.lireGalerie(dossier)
            index.keys().asSequence().map { it to index.getJSONObject(it) }.sortedBy { it.first }.toList()
        }
    }
    if (photos.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text(stringResource(R.string.galerie_vide), Modifier.padding(24.dp)) }
        return
    }
    // la meilleure photo de chaque espèce (le ménage n'y touche pas)
    LazyVerticalGrid(GridCells.Adaptive(160.dp), Modifier.fillMaxSize(), contentPadding = PaddingValues(12.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        itemsGrille(photos, key = { it.first }) { (espece, e) ->
            Card(colors = CardDefaults.cardColors(containerColor = Couleurs.carte, contentColor = Couleurs.texte),
                modifier = Modifier.clickable { ouvrirClip(context, File(dossier, File(e.optString("video")).name)) }) {
                Column {
                    Miniature(File(dossier, e.optString("photo")), Modifier.fillMaxWidth().aspectRatio(1f), echantillon = 1)
                    Column(Modifier.padding(8.dp)) {
                        Text(espece, fontWeight = FontWeight.Bold, maxLines = 2)
                        Text("${e.optString("date")}  ·  ${((e.optString("confiance").toFloatOrNull() ?: 0f) * 100).toInt()} %",
                            style = MaterialTheme.typography.bodySmall, color = Couleurs.discret)
                    }
                }
            }
        }
    }
}

@Composable
private fun Statistiques() {
    val context = LocalContext.current
    val version by Etat.versionJournal.collectAsStateWithLifecycle()
    var visites by remember { mutableStateOf(emptyList<Map<String, String>>()) }
    var jours by rememberSaveable { mutableIntStateOf(30) }
    LaunchedEffect(version) {
        visites = withContext(Dispatchers.IO) { Journal(dossierVisites(context)).lire().filter { it["espece"] != PAS_UN_OISEAU } }
    }
    val format = remember { java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US) }
    val maintenant = System.currentTimeMillis()
    val debut = if (jours > 0) format.format(java.util.Date(maintenant - (jours - 1) * 86_400_000L)) else ""
    val choix = visites.filter { it["date"].orEmpty() >= debut }
    val especes = choix.filter { it["espece"] != INCONNU }.groupingBy { it["espece"].orEmpty() }.eachCount()
        .entries.sortedByDescending { it.value }
    Column(Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((valeur, texte) in listOf(7 to R.string.jours_7, 30 to R.string.jours_30, 0 to R.string.tout))
                FilterChip(jours == valeur, { jours = valeur }, { Text(stringResource(texte)) })
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Chiffre(choix.size.toString(), stringResource(R.string.stat_visites), Modifier.weight(1f))
            Chiffre(especes.size.toString(), stringResource(R.string.stat_especes), Modifier.weight(1f))
        }
        Chiffre(especes.firstOrNull()?.key ?: "—", stringResource(R.string.stat_plus_frequente), Modifier.fillMaxWidth())
        Carte(stringResource(R.string.visites_par_espece)) {
            if (especes.isEmpty()) Text(stringResource(R.string.aucune_visite_periode), color = Couleurs.discret)
            val couleurs = listOf(0xFF58A6FF, 0xFF3FB950, 0xFFD29922, 0xFFF778BA, 0xFFA371F7, 0xFF79C0FF, 0xFFFFA657, 0xFF7EE787)
            especes.take(15).forEachIndexed { i, (espece, n) ->
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 3.dp)) {
                    Text(espece, Modifier.width(140.dp), maxLines = 1, style = MaterialTheme.typography.bodySmall)
                    Box(Modifier.weight(1f).height(12.dp)) {
                        Box(Modifier.fillMaxWidth(n.toFloat() / especes[0].value).fillMaxHeight().background(Color(couleurs[i % couleurs.size])))
                    }
                    Text(" $n", style = MaterialTheme.typography.bodySmall, color = Couleurs.discret)
                }
            }
        }
        val heures = IntArray(24).also { h -> choix.forEach { l -> l["heure"]?.take(2)?.toIntOrNull()?.let { if (it in 0..23) h[it]++ } } }
        Carte(stringResource(R.string.visites_par_heure)) { Colonnes(heures.toList(), (0 until 24).map { "${it}h" }, 3) }
        val nbJours = if (jours > 0) jours else choix.minOfOrNull { it["date"].orEmpty() }?.let { d ->
            runCatching { ((maintenant - format.parse(d)!!.time) / 86_400_000L).toInt() + 1 }.getOrNull() } ?: 1
        val dates = (0 until nbJours.coerceIn(1, 366)).map { java.util.Date(maintenant - (nbJours - 1 - it) * 86_400_000L) }
        val parJour = choix.groupingBy { it["date"].orEmpty() }.eachCount()
        val court = remember { java.text.SimpleDateFormat("dd/MM", Locale.US) }
        Carte(stringResource(R.string.visites_par_jour)) {
            Colonnes(dates.map { parJour[format.format(it)] ?: 0 }, dates.map { court.format(it) }, maxOf(1, dates.size / 6))
        }
    }
}

@Composable
private fun Chiffre(valeur: String, texte: String, m: Modifier) {
    Column(m.background(Couleurs.carte, androidx.compose.foundation.shape.RoundedCornerShape(10.dp)).padding(14.dp)) {
        Text(valeur, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold, maxLines = 1)
        Text(texte, style = MaterialTheme.typography.bodySmall, color = Couleurs.discret)
    }
}

@Composable
private fun Carte(titre: String, contenu: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxWidth().background(Couleurs.carte, androidx.compose.foundation.shape.RoundedCornerShape(10.dp)).padding(14.dp)) {
        Text(titre, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(bottom = 8.dp))
        contenu()
    }
}

/** Histogramme en colonnes (visites par heure, par jour), comme la fenêtre Statistiques du PC. */
@Composable
private fun Colonnes(valeurs: List<Int>, etiquettes: List<String>, pasEtiquette: Int) {
    val maxi = maxOf(1, valeurs.maxOrNull() ?: 0)
    Text("max $maxi", style = MaterialTheme.typography.labelSmall, color = Couleurs.discret, modifier = Modifier.fillMaxWidth(),
        textAlign = androidx.compose.ui.text.style.TextAlign.End)
    Canvas(Modifier.fillMaxWidth().height(110.dp)) {
        val pas = size.width / valeurs.size
        valeurs.forEachIndexed { i, v ->
            if (v > 0) {
                val h = size.height * v / maxi
                drawRect(Couleurs.bleu, Offset(i * pas + pas * 0.15f, size.height - h), Size(pas * 0.7f, h))
            }
        }
    }
    Row(Modifier.fillMaxWidth()) {
        etiquettes.forEachIndexed { i, e ->
            Text(if (i % pasEtiquette == 0) e else "", Modifier.weight(1f), style = MaterialTheme.typography.labelSmall,
                color = Couleurs.discret, maxLines = 1, softWrap = false)
        }
    }
}
