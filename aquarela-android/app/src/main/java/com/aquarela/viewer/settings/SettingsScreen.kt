package com.aquarela.viewer.settings

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
