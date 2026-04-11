package com.aquarela.viewer.sessions

import android.widget.Toast
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aquarela.viewer.data.Maneuver
import com.aquarela.viewer.data.Session
import com.aquarela.viewer.util.CsvDownloader
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SessionDetailScreen(
    sessionId: Int,
    piBaseUrl: String? = null,
    onBack: () -> Unit,
    vm: SessionDetailViewModel = viewModel(),
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    LaunchedEffect(sessionId) { vm.load(sessionId) }
    val detail by vm.detail.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sessione") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                    }
                },
                actions = {
                    val d = detail
                    if (d != null && d.session.csv_file != null && piBaseUrl != null) {
                        IconButton(onClick = {
                            scope.launch {
                                val fileName = CsvDownloader.download(context, piBaseUrl, d.session.csv_file!!)
                                if (fileName != null) {
                                    Toast.makeText(context, "Salvato in Download: $fileName", Toast.LENGTH_LONG).show()
                                } else {
                                    Toast.makeText(context, "Download fallito — Pi raggiungibile?", Toast.LENGTH_SHORT).show()
                                }
                            }
                        }) {
                            Icon(Icons.Default.Share, "Download CSV")
                        }
                    }
                },
            )
        },
    ) { padding ->
        val d = detail
        if (d == null) {
            Box(Modifier.fillMaxSize().padding(padding))
        } else {
            Column(Modifier.fillMaxSize().padding(padding)) {
                // Stats + maneuvers scroll independently
                Column(
                    Modifier.weight(1f).verticalScroll(rememberScrollState()),
                ) {
                    StatsSection(d.session)
                    ManeuversSection(d.maneuvers)
                }
                // Map pinned at bottom, never overlaps
                if (d.trackPoints.isNotEmpty()) {
                    TrackMapView(
                        trackPoints = d.trackPoints,
                        maneuvers = d.maneuvers,
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f)
                            .padding(12.dp)
                            .clip(RoundedCornerShape(12.dp)),
                    )
                }
            }
        }
    }
}

@Composable
private fun StatsSection(s: Session) {
    Column(Modifier.padding(12.dp)) {
        Text("Statistiche", style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatCard("Durata", formatDuration(s.duration_secs))
            StatCard("Distanza", "%.1f nm".format(s.distance_nm))
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatCard("BSP", "%.1f / %.1f kt".format(s.avg_bsp_kt, s.max_bsp_kt))
            StatCard("VMG", "%.1f kt".format(s.avg_vmg_kt))
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
            StatCard("Vento", "TWS %.0f kt".format(s.avg_tws_kt))
            if (s.avg_vmc_kt != null) {
                StatCard("VMC", "%.1f kt".format(s.avg_vmc_kt))
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String) {
    Card(Modifier.width(160.dp)) {
        Column(Modifier.padding(12.dp)) {
            Text(label, style = MaterialTheme.typography.labelSmall)
            Text(value, style = MaterialTheme.typography.titleLarge)
        }
    }
}

@Composable
private fun ManeuversSection(maneuvers: List<Maneuver>) {
    Column(Modifier.padding(12.dp)) {
        Text("Manovre", style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(8.dp))
        if (maneuvers.isEmpty()) {
            Text("Nessuna manovra registrata.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            val tacks = maneuvers.filter { it.maneuver_type == "tack" }
            val gybes = maneuvers.filter { it.maneuver_type == "gybe" }
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("Virate: ${tacks.size}  |  Strambate: ${gybes.size}")
                    Text("Recovery medio: %.1fs".format(maneuvers.map { it.recovery_secs }.average()))
                    Text("Distanza persa: %.0f m".format(maneuvers.map { it.vmg_loss_nm * 1852 }.average()))
                }
            }
        }
    }
}
