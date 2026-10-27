package io.github.oli97430.becquee

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
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
            SurveillanceService.lancer(this, SurveillanceService.FICHIER, Uri.fromFile(video))
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
            NavigationBarItem(onglet == 2, { onglet = 2 }, { Icon(Icons.Default.Settings, null) }, label = { Text(stringResource(R.string.onglet_reglages)) })
        }
    }) { marges ->
        Box(Modifier.padding(marges).fillMaxSize()) {
            when (onglet) {
                0 -> Direct()
                1 -> Visites()
                else -> ReglagesEcran()
            }
        }
    }
}

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
    Column(Modifier.fillMaxSize().padding(12.dp)) {
        Box(Modifier.fillMaxWidth().weight(1f).background(Color(0xFF05080B)), contentAlignment = Alignment.Center) {
            val b = image
            if (b == null) Text(stringResource(R.string.aucune_image))
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
        Text(buildString {
            if (marche != null) append(String.format(Locale.getDefault(), "%.0f i/s", vue.fps))
            if (vue.enregistrement) append("  ●  " + String.format(Locale.getDefault(), "%.0f s", vue.duree))
            if (vue.etiquette.isNotEmpty()) append("  ${vue.etiquette}")
        }, fontWeight = FontWeight.Bold)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
            if (marche == null) {
                Button({
                    val demandees = mutableListOf(Manifest.permission.CAMERA)
                    if (Build.VERSION.SDK_INT >= 33) demandees.add(Manifest.permission.POST_NOTIFICATIONS)
                    permissions.launch(demandees.toTypedArray())
                }) { Text(stringResource(R.string.demarrer)) }
                OutlinedButton({ choisirVideo.launch(arrayOf("video/*")) }) { Text(stringResource(R.string.analyser_video)) }
            } else Button({ SurveillanceService.lancer(context, SurveillanceService.ARRETER) }) { Text(stringResource(R.string.arreter)) }
        }
        Column(Modifier.height(110.dp).verticalScroll(rememberScrollState())) {
            messages.takeLast(8).reversed().forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
        }
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
private fun Miniature(photo: File) {
    val b by produceState<android.graphics.Bitmap?>(null, photo) {
        value = withContext(Dispatchers.IO) {
            if (!photo.isFile) null else BitmapFactory.decodeFile(photo.path, BitmapFactory.Options().apply { inSampleSize = 4 })
        }
    }
    Box(Modifier.size(96.dp, 72.dp)) {
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
        HorizontalDivider()
        Text(stringResource(R.string.dossier, dossierVisites(context).path), style = MaterialTheme.typography.bodySmall)
    }
}
