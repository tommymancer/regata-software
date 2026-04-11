package com.aquarela.viewer.sessions

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aquarela.viewer.data.Session

@Composable
fun SessionListScreen(
    onSessionClick: (Int) -> Unit,
    vm: SessionListViewModel = viewModel(),
) {
    val sessions by vm.sessions.collectAsState(initial = emptyList())

    if (sessions.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(
                "Nessuna sessione.\nConnettiti al Pi per sincronizzare.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    } else {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(sessions, key = { it.id }) { session ->
                SessionCard(session, onClick = { onSessionClick(session.id) })
            }
        }
    }
}

@Composable
private fun SessionCard(session: Session, onClick: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(16.dp)) {
            Text(
                formatDate(session.start_time),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(4.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(formatDuration(session.duration_secs))
                Text("%.1f nm".format(session.distance_nm))
                Text("TWS %.0f kt".format(session.avg_tws_kt))
            }
        }
    }
}

internal fun formatDate(iso: String): String {
    return try {
        val instant = java.time.Instant.parse(iso)
        val zoned = instant.atZone(java.time.ZoneId.systemDefault())
        val fmt = java.time.format.DateTimeFormatter.ofPattern("d MMM yyyy — HH:mm")
        zoned.format(fmt)
    } catch (_: Exception) { iso }
}

internal fun formatDuration(secs: Int): String {
    val h = secs / 3600
    val m = (secs % 3600) / 60
    return if (h > 0) "${h}h ${m}m" else "${m}m"
}
