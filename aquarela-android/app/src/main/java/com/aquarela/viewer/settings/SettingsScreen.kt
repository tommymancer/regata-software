package com.aquarela.viewer.settings

import android.content.Intent
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.widget.Toast
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

private const val GITHUB_TARBALL =
    "https://api.github.com/repos/tommymancer/regata-software/tarball/master"

private const val GITHUB_COMMITS =
    "https://api.github.com/repos/tommymancer/regata-software/commits/master"

@Composable
fun SettingsScreen(piBaseUrl: String?) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var currentVersion by remember { mutableStateOf<String?>(null) }
    var latestVersion by remember { mutableStateOf<String?>(null) }
    var updating by remember { mutableStateOf(false) }
    var updateStatus by remember { mutableStateOf<String?>(null) }
    var updateResult by remember { mutableStateOf<String?>(null) }

    // Fetch current Pi version + latest GitHub version
    LaunchedEffect(piBaseUrl) {
        // Pi version
        if (piBaseUrl != null) {
            withContext(Dispatchers.IO) {
                try {
                    val json = httpGet("$piBaseUrl/api/system/version")
                    val obj = JSONObject(json)
                    currentVersion = obj.optString("sha", "?").take(7) +
                            " — " + obj.optString("message", "")
                } catch (_: Exception) {
                    currentVersion = "non raggiungibile"
                }
            }
        }
        // GitHub latest (via cellular, unbind from WiFi)
        withContext(Dispatchers.IO) {
            val cm = context.getSystemService(ConnectivityManager::class.java)
            cm.bindProcessToNetwork(null)
            try {
                val json = httpGet(GITHUB_COMMITS)
                val obj = JSONObject(json)
                val sha = obj.optString("sha", "?").take(7)
                val msg = obj.optJSONObject("commit")?.optString("message", "") ?: ""
                latestVersion = "$sha — ${msg.lines().first()}"
            } catch (_: Exception) {
                latestVersion = "impossibile verificare"
            } finally {
                val wifiNet = cm.allNetworks.firstOrNull { net ->
                    cm.getNetworkCapabilities(net)
                        ?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true
                }
                cm.bindProcessToNetwork(wifiNet)
            }
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text("Impostazioni", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(24.dp))

        // Connection status
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {
                Text("Connessione Pi", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                if (piBaseUrl != null) {
                    Text("Connesso: $piBaseUrl",
                        color = MaterialTheme.colorScheme.primary)
                } else {
                    Text("Non connesso — apri la tab Live",
                        color = MaterialTheme.colorScheme.error)
                }
            }
        }

        Spacer(Modifier.height(16.dp))

        // Software update
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {
                Text("Aggiornamento Software", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))

                Text("Pi: ${currentVersion ?: "caricamento..."}")
                Text("GitHub: ${latestVersion ?: "caricamento..."}")

                Spacer(Modifier.height(12.dp))

                Button(
                    onClick = {
                        if (piBaseUrl == null) {
                            Toast.makeText(context, "Pi non connesso", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        updating = true
                        updateStatus = "Scaricamento da GitHub..."
                        updateResult = null
                        scope.launch {
                            try {
                                val cm = context.getSystemService(ConnectivityManager::class.java)

                                // 1. Download tarball from GitHub via cellular
                                //    Unbind from WiFi so traffic goes through cellular
                                val tarball = withContext(Dispatchers.IO) {
                                    cm.bindProcessToNetwork(null)
                                    try {
                                        downloadBytes(GITHUB_TARBALL)
                                    } finally {
                                        // Re-bind to WiFi for Pi communication
                                        val wifiNet = cm.allNetworks.firstOrNull { net ->
                                            cm.getNetworkCapabilities(net)
                                                ?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true
                                        }
                                        cm.bindProcessToNetwork(wifiNet)
                                    }
                                }
                                updateStatus = "Invio al Pi (${tarball.size / 1024} KB)..."

                                // 2. Upload to Pi (already re-bound to WiFi)
                                val json = withContext(Dispatchers.IO) {
                                    httpPostBytes("$piBaseUrl/api/system/update", tarball)
                                }
                                val obj = JSONObject(json)
                                val success = obj.optBoolean("success", false)
                                val steps = obj.optJSONArray("steps")
                                val summary = buildString {
                                    if (success) append("Aggiornamento completato!\n")
                                    else append("Aggiornamento fallito\n")
                                    if (steps != null) {
                                        for (i in 0 until steps.length()) {
                                            val s = steps.getJSONObject(i)
                                            val icon = if (s.optBoolean("ok")) "✓" else "✗"
                                            append("$icon ${s.optString("step")}: ${s.optString("output")}\n")
                                        }
                                    }
                                }
                                updateResult = summary
                                updateStatus = null

                                if (success) {
                                    // Refresh version after restart
                                    kotlinx.coroutines.delay(5000)
                                    try {
                                        val vJson = withContext(Dispatchers.IO) {
                                            httpGet("$piBaseUrl/api/system/version")
                                        }
                                        val v = JSONObject(vJson)
                                        currentVersion = v.optString("sha", "?").take(7) +
                                                " — " + v.optString("message", "")
                                    } catch (_: Exception) {}
                                }
                            } catch (e: Exception) {
                                updateResult = "Errore: ${e.message}"
                                updateStatus = null
                            }
                            updating = false
                        }
                    },
                    enabled = !updating && piBaseUrl != null,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (updating) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = MaterialTheme.colorScheme.onPrimary,
                            strokeWidth = 2.dp,
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(updateStatus ?: "Aggiornamento in corso...")
                    } else {
                        Text("Aggiorna Pi da GitHub")
                    }
                }

                if (updateResult != null) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        updateResult!!,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        Spacer(Modifier.height(16.dp))

        // Diagnostics section
        var diagRunning by remember { mutableStateOf(false) }
        var canDumpRunning by remember { mutableStateOf(false) }
        var bleScanRunning by remember { mutableStateOf(false) }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {
                Text("Diagnostica", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(4.dp))
                Text(
                    "Condividi i report su Telegram per assistenza remota",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(12.dp))

                // Diagnostica button (health + logs)
                Button(
                    onClick = {
                        if (piBaseUrl == null) {
                            Toast.makeText(context, "Pi non connesso", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        diagRunning = true
                        scope.launch {
                            try {
                                val report = withContext(Dispatchers.IO) {
                                    val health = httpGet("$piBaseUrl/api/system/health")
                                    val logs = httpGet("$piBaseUrl/api/system/logs?lines=20")
                                    formatDiagReport(health, logs)
                                }
                                shareText(context, "Diagnostica Aquarela", report)
                            } catch (e: Exception) {
                                Toast.makeText(context, "Errore: ${e.message}", Toast.LENGTH_SHORT).show()
                            }
                            diagRunning = false
                        }
                    },
                    enabled = !diagRunning && piBaseUrl != null,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (diagRunning) {
                        CircularProgressIndicator(
                            Modifier.size(20.dp),
                            color = MaterialTheme.colorScheme.onPrimary,
                            strokeWidth = 2.dp,
                        )
                        Spacer(Modifier.width(8.dp))
                    }
                    Text("Diagnostica")
                }

                Spacer(Modifier.height(8.dp))

                // CAN Dump button
                Button(
                    onClick = {
                        if (piBaseUrl == null) {
                            Toast.makeText(context, "Pi non connesso", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        canDumpRunning = true
                        scope.launch {
                            try {
                                val report = withContext(Dispatchers.IO) {
                                    val json = httpPostJson(
                                        "$piBaseUrl/api/system/can-dump",
                                        """{"seconds":30}""",
                                    )
                                    formatCanDump(json)
                                }
                                shareText(context, "CAN Dump Aquarela", report)
                            } catch (e: Exception) {
                                Toast.makeText(context, "Errore: ${e.message}", Toast.LENGTH_SHORT).show()
                            }
                            canDumpRunning = false
                        }
                    },
                    enabled = !canDumpRunning && piBaseUrl != null,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.secondaryContainer,
                        contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
                    ),
                ) {
                    if (canDumpRunning) {
                        CircularProgressIndicator(
                            Modifier.size(20.dp),
                            color = MaterialTheme.colorScheme.onSecondaryContainer,
                            strokeWidth = 2.dp,
                        )
                        Spacer(Modifier.width(8.dp))
                        Text("CAN Dump (30s)...")
                    } else {
                        Text("CAN Dump")
                    }
                }

                Spacer(Modifier.height(8.dp))

                // BLE Scan button
                Button(
                    onClick = {
                        if (piBaseUrl == null) {
                            Toast.makeText(context, "Pi non connesso", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        bleScanRunning = true
                        scope.launch {
                            try {
                                val report = withContext(Dispatchers.IO) {
                                    val json = httpGet("$piBaseUrl/api/system/ble-scan")
                                    formatBleScan(json)
                                }
                                shareText(context, "BLE Scan Aquarela", report)
                            } catch (e: Exception) {
                                Toast.makeText(context, "Errore: ${e.message}", Toast.LENGTH_SHORT).show()
                            }
                            bleScanRunning = false
                        }
                    },
                    enabled = !bleScanRunning && piBaseUrl != null,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.secondaryContainer,
                        contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
                    ),
                ) {
                    if (bleScanRunning) {
                        CircularProgressIndicator(
                            Modifier.size(20.dp),
                            color = MaterialTheme.colorScheme.onSecondaryContainer,
                            strokeWidth = 2.dp,
                        )
                        Spacer(Modifier.width(8.dp))
                        Text("BLE Scan (10s)...")
                    } else {
                        Text("BLE Scan")
                    }
                }
            }
        }
    }
}

private fun httpGet(url: String): String {
    val conn = URL(url).openConnection() as HttpURLConnection
    conn.connectTimeout = 5_000
    conn.readTimeout = 10_000
    return try {
        if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
        conn.inputStream.bufferedReader().readText()
    } finally {
        conn.disconnect()
    }
}

/** Download binary content, following redirects. */
private fun downloadBytes(url: String): ByteArray {
    val conn = URL(url).openConnection() as HttpURLConnection
    conn.connectTimeout = 10_000
    conn.readTimeout = 60_000
    conn.instanceFollowRedirects = true
    return try {
        if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
        conn.inputStream.readBytes()
    } finally {
        conn.disconnect()
    }
}

/** POST JSON string to URL, return response body. */
private fun httpPostJson(url: String, jsonBody: String): String {
    val conn = URL(url).openConnection() as HttpURLConnection
    conn.connectTimeout = 10_000
    conn.readTimeout = 60_000
    conn.requestMethod = "POST"
    conn.doOutput = true
    conn.setRequestProperty("Content-Type", "application/json")
    return try {
        conn.outputStream.use { it.write(jsonBody.toByteArray()) }
        if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
        conn.inputStream.bufferedReader().readText()
    } finally {
        conn.disconnect()
    }
}

/** POST raw bytes to URL, return response body. */
private fun httpPostBytes(url: String, data: ByteArray): String {
    val conn = URL(url).openConnection() as HttpURLConnection
    conn.connectTimeout = 10_000
    conn.readTimeout = 180_000  // extraction + npm build can be slow
    conn.requestMethod = "POST"
    conn.doOutput = true
    conn.setRequestProperty("Content-Type", "application/gzip")
    conn.setRequestProperty("Content-Length", data.size.toString())
    return try {
        conn.outputStream.use { it.write(data) }
        if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
        conn.inputStream.bufferedReader().readText()
    } finally {
        conn.disconnect()
    }
}

// ── Diagnostic report formatters ──────────────────────────────────────

/** Format health + logs into a readable text report for Telegram. */
private fun formatDiagReport(healthJson: String, logsJson: String): String {
    val h = JSONObject(healthJson)
    val version = h.optJSONObject("version")
    val sensors = h.optJSONObject("sensor_ages_ms")
    val sb = StringBuilder()

    sb.appendLine("AQUARELA DIAGNOSTICA")
    sb.appendLine("====================")
    sb.appendLine("Barca: ${h.optString("boat_name", "?")}")
    sb.appendLine("Versione: ${version?.optString("sha", "?")} - ${version?.optString("message", "")}")
    sb.appendLine("Uptime: ${h.optInt("uptime_s", 0) / 60} min")
    sb.appendLine("Source: ${h.optString("source", "?")}")
    sb.appendLine()

    sb.appendLine("SENSORI (age ms):")
    if (sensors != null) {
        for (key in sensors.keys()) {
            val age = sensors.optInt(key, -1)
            val status = when {
                age < 500 -> "OK"
                age < 5000 -> "LENTO"
                else -> "NON RISPONDE"
            }
            sb.appendLine("  $key: $age ms ($status)")
        }
    }
    sb.appendLine()

    sb.appendLine("SISTEMA:")
    val cpuTemp = h.opt("cpu_temp_c")
    if (cpuTemp != null && cpuTemp != JSONObject.NULL) sb.appendLine("  CPU: ${cpuTemp}C")
    sb.appendLine("  Disco libero: ${h.optInt("disk_free_mb", 0)} MB")
    sb.appendLine("  Pipeline: ${h.optInt("pipeline_hz", 0)} Hz")
    sb.appendLine("  Sessione attiva: ${if (h.optBoolean("session_active")) "SI" else "NO"}")
    sb.appendLine("  CSV logging: ${if (h.optBoolean("csv_logging")) "SI" else "NO"}")
    sb.appendLine("  Errori ultima ora: ${h.optInt("errors_last_hour", 0)}")
    sb.appendLine()

    // Last few log lines
    val logsObj = JSONObject(logsJson)
    val lines = logsObj.optJSONArray("lines")
    if (lines != null && lines.length() > 0) {
        sb.appendLine("LOG (ultime ${lines.length()} righe):")
        for (i in 0 until lines.length()) {
            sb.appendLine("  ${lines.optString(i)}")
        }
    }

    return sb.toString()
}

/** Format CAN dump into a readable text report. */
private fun formatCanDump(json: String): String {
    val obj = JSONObject(json)
    val sb = StringBuilder()

    sb.appendLine("AQUARELA CAN DUMP")
    sb.appendLine("=================")
    sb.appendLine("Durata: ${obj.optInt("duration_s")}s")
    sb.appendLine("Frame totali: ${obj.optInt("frames_total")}")

    val note = obj.optString("note", "")
    if (note.isNotEmpty()) {
        sb.appendLine(note)
        return sb.toString()
    }

    val error = obj.optString("error", "")
    if (error.isNotEmpty()) {
        sb.appendLine("ERRORE: $error")
        return sb.toString()
    }

    sb.appendLine()
    sb.appendLine("PGN RICONOSCIUTI:")
    val pgns = obj.optJSONObject("pgns_seen")
    if (pgns != null) {
        for (key in pgns.keys()) {
            val p = pgns.getJSONObject(key)
            sb.appendLine("  PGN $key (${p.optString("desc", "?")}): ${p.optInt("count")} frame, ${p.optDouble("hz", 0.0)} Hz, src=${p.optJSONArray("sources")}")
        }
    }

    val unknown = obj.optJSONObject("unknown_pgns")
    if (unknown != null && unknown.length() > 0) {
        sb.appendLine()
        sb.appendLine("PGN SCONOSCIUTI:")
        for (key in unknown.keys()) {
            val p = unknown.getJSONObject(key)
            sb.appendLine("  PGN $key: ${p.optInt("count")} frame, src=${p.optJSONArray("sources")}")
        }
    }

    val addrs = obj.optJSONObject("source_addresses")
    if (addrs != null && addrs.length() > 0) {
        sb.appendLine()
        sb.appendLine("INDIRIZZI SORGENTE:")
        for (key in addrs.keys()) {
            sb.appendLine("  Addr $key: ${addrs.optInt(key)} frame")
        }
    }

    return sb.toString()
}

/** Format BLE scan into a readable text report. */
private fun formatBleScan(json: String): String {
    val obj = JSONObject(json)
    val sb = StringBuilder()

    sb.appendLine("AQUARELA BLE SCAN")
    sb.appendLine("=================")

    val error = obj.optString("error", "")
    if (error.isNotEmpty()) {
        sb.appendLine("ERRORE: $error")
        return sb.toString()
    }

    val devices = obj.optJSONArray("devices")
    if (devices == null || devices.length() == 0) {
        sb.appendLine("Nessun dispositivo BLE trovato")
        return sb.toString()
    }

    sb.appendLine("${devices.length()} dispositivi trovati:")
    sb.appendLine()
    for (i in 0 until devices.length()) {
        val d = devices.getJSONObject(i)
        sb.appendLine("  ${d.optString("name", "?")} | ${d.optString("mac")} | RSSI: ${d.optInt("rssi")} dBm")
    }

    return sb.toString()
}

/** Open Android share sheet with text content. */
private fun shareText(context: android.content.Context, subject: String, text: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_SUBJECT, subject)
        putExtra(Intent.EXTRA_TEXT, text)
    }
    context.startActivity(Intent.createChooser(intent, "Condividi diagnostica"))
}
