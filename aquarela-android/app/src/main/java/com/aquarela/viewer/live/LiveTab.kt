package com.aquarela.viewer.live

import android.annotation.SuppressLint
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiNetworkSuggestion
import android.net.wifi.WifiManager
import android.os.Environment
import android.content.ContentValues
import android.provider.MediaStore
import android.util.Log
import android.view.ViewGroup
import android.webkit.*
import android.widget.Toast
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

private const val TAG = "AquarelaViewer"
private const val HOTSPOT_IP = "10.42.0.1"
private const val PORT = 8080
private const val PROBE_PATH = "/api/source"
private const val PROBE_TIMEOUT_MS = 3000
private const val AQUARELA_SSID = "Aquarela"
private const val AQUARELA_PSK = "aquarela1"
private const val NSD_SERVICE_TYPE = "_http._tcp."

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun LiveTab(onPiFound: (String) -> Unit) {
    val context = LocalContext.current
    var resolvedUrl by remember { mutableStateOf<String?>(null) }
    var nsdDiscoveryActive by remember { mutableStateOf(false) }

    val connectivityManager = remember { context.getSystemService(ConnectivityManager::class.java) }
    val nsdManager = remember { context.getSystemService(NsdManager::class.java) }

    val webView = remember {
        WebView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                loadWithOverviewMode = true
                useWideViewPort = true
                cacheMode = WebSettings.LOAD_NO_CACHE
            }
            clearCache(true)
            CookieManager.getInstance().removeAllCookies(null)
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()

            setDownloadListener { url, userAgent, contentDisposition, mimeType, _ ->
                val filename = URLUtil.guessFileName(url, contentDisposition, mimeType)
                Toast.makeText(context, "Downloading $filename…", Toast.LENGTH_SHORT).show()
                thread(name = "aquarela-download") {
                    try {
                        val conn = URL(url).openConnection() as HttpURLConnection
                        conn.setRequestProperty("User-Agent", userAgent)
                        conn.connectTimeout = 10_000
                        conn.readTimeout = 30_000
                        conn.connect()
                        if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
                        val bytes = conn.inputStream.use { it.readBytes() }
                        conn.disconnect()
                        val values = ContentValues().apply {
                            put(MediaStore.Downloads.DISPLAY_NAME, filename)
                            put(MediaStore.Downloads.MIME_TYPE, mimeType ?: "text/csv")
                            put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                        }
                        val uri = context.contentResolver.insert(
                            MediaStore.Downloads.EXTERNAL_CONTENT_URI, values
                        ) ?: throw Exception("Failed to create file in Downloads")
                        context.contentResolver.openOutputStream(uri)!!.use { it.write(bytes) }
                        (context as? android.app.Activity)?.runOnUiThread {
                            Toast.makeText(context, "$filename saved to Downloads", Toast.LENGTH_SHORT).show()
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Download failed", e)
                        (context as? android.app.Activity)?.runOnUiThread {
                            Toast.makeText(context, "Download failed: ${e.message}", Toast.LENGTH_LONG).show()
                        }
                    }
                }
            }
        }
    }

    fun probeHost(host: String): String? {
        return try {
            val url = URL("http://$host:$PORT$PROBE_PATH")
            val conn = url.openConnection() as HttpURLConnection
            conn.connectTimeout = PROBE_TIMEOUT_MS
            conn.readTimeout = PROBE_TIMEOUT_MS
            conn.requestMethod = "GET"
            val code = conn.responseCode
            conn.disconnect()
            if (code == 200) "http://$host:$PORT" else null
        } catch (e: Exception) { null }
    }

    fun onFound(url: String) {
        if (resolvedUrl != null) return
        resolvedUrl = url
        onPiFound(url)
        (context as? android.app.Activity)?.runOnUiThread {
            webView.loadUrl(url)
        }
    }

    DisposableEffect(Unit) {
        val suggestion = WifiNetworkSuggestion.Builder()
            .setSsid(AQUARELA_SSID)
            .setWpa2Passphrase(AQUARELA_PSK)
            .setIsAppInteractionRequired(false)
            .build()
        val wifiManager = context.getSystemService(WifiManager::class.java)
        wifiManager.addNetworkSuggestions(listOf(suggestion))

        val nsdListener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String) {}
            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                if (serviceInfo.serviceName.contains("aquarela", ignoreCase = true)) {
                    nsdManager?.resolveService(serviceInfo, object : NsdManager.ResolveListener {
                        override fun onResolveFailed(si: NsdServiceInfo, err: Int) {}
                        override fun onServiceResolved(si: NsdServiceInfo) {
                            val host = si.host?.hostAddress ?: return
                            onFound("http://$host:${si.port}")
                        }
                    })
                }
            }
            override fun onServiceLost(serviceInfo: NsdServiceInfo) {}
            override fun onDiscoveryStopped(serviceType: String) {}
            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {}
            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {}
        }

        val networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                connectivityManager.bindProcessToNetwork(network)
                thread(name = "aquarela-probe") {
                    probeHost(HOTSPOT_IP)?.let { onFound(it) }
                }
                if (!nsdDiscoveryActive) {
                    try {
                        nsdManager?.discoverServices(NSD_SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, nsdListener)
                        nsdDiscoveryActive = true
                    } catch (_: Exception) {}
                }
            }
            override fun onLost(network: Network) {
                resolvedUrl = null
                connectivityManager.bindProcessToNetwork(null)
            }
        }

        val request = NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()
        connectivityManager.requestNetwork(request, networkCallback)

        thread(name = "aquarela-direct-fallback") {
            Thread.sleep(5000)
            if (resolvedUrl != null) return@thread
            connectivityManager.bindProcessToNetwork(null)
            for (host in listOf("localhost", "aquarela.local", "192.168.1.138", HOTSPOT_IP, "10.42.1.1", "10.0.2.2")) {
                if (resolvedUrl != null) return@thread
                probeHost(host)?.let { onFound(it); return@thread }
            }
        }

        onDispose {
            connectivityManager.bindProcessToNetwork(null)
            if (nsdDiscoveryActive) {
                try { nsdManager?.stopServiceDiscovery(nsdListener) } catch (_: Exception) {}
            }
            try { connectivityManager.unregisterNetworkCallback(networkCallback) } catch (_: Exception) {}
        }
    }

    AndroidView(factory = { webView }, modifier = Modifier.fillMaxSize())
}
