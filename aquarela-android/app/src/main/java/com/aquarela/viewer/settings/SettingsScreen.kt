package com.aquarela.viewer.settings

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

@Composable
fun SettingsScreen(piBaseUrl: String?) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var currentVersion by remember { mutableStateOf<String?>(null) }
    var updating by remember { mutableStateOf(false) }
    var updateResult by remember { mutableStateOf<String?>(null) }

    // Fetch current version on load
    LaunchedEffect(piBaseUrl) {
        if (piBaseUrl == null) return@LaunchedEffect
        withContext(Dispatchers.IO) {
            try {
                val json = httpGet("$piBaseUrl/api/system/version")
                val obj = JSONObject(json)
                currentVersion = "${obj.optString("sha", "?")} — ${obj.optString("message", "")}"
            } catch (_: Exception) {
                currentVersion = "non raggiungibile"
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

                Text("Versione attuale: ${currentVersion ?: "caricamento..."}")

                Spacer(Modifier.height(12.dp))

                Button(
                    onClick = {
                        if (piBaseUrl == null) {
                            Toast.makeText(context, "Pi non connesso", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        updating = true
                        updateResult = null
                        scope.launch {
                            try {
                                val json = withContext(Dispatchers.IO) {
                                    httpPost("$piBaseUrl/api/system/update")
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
                                if (success) {
                                    // Refresh version after restart
                                    kotlinx.coroutines.delay(5000)
                                    try {
                                        val vJson = withContext(Dispatchers.IO) {
                                            httpGet("$piBaseUrl/api/system/version")
                                        }
                                        val v = JSONObject(vJson)
                                        currentVersion = "${v.optString("sha", "?")} — ${v.optString("message", "")}"
                                    } catch (_: Exception) {}
                                }
                            } catch (e: Exception) {
                                updateResult = "Errore: ${e.message}"
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
                        Text("Aggiornamento in corso...")
                    } else {
                        Text("Aggiorna da GitHub")
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

private fun httpPost(url: String): String {
    val conn = URL(url).openConnection() as HttpURLConnection
    conn.connectTimeout = 10_000
    conn.readTimeout = 120_000
    conn.requestMethod = "POST"
    conn.doOutput = true
    conn.outputStream.write(ByteArray(0))
    return try {
        if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
        conn.inputStream.bufferedReader().readText()
    } finally {
        conn.disconnect()
    }
}
