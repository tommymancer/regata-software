package com.aquarela.viewer.settings

import android.annotation.SuppressLint
import android.view.ViewGroup
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView

/**
 * Full-screen WebView that loads a Svelte tool page via hash routing.
 *
 * Example: piBaseUrl = "http://10.42.0.1:8080", pageName = "calibration"
 *          → loads "http://10.42.0.1:8080/#calibration"
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun ToolPageScreen(piBaseUrl: String, pageName: String, onBack: () -> Unit) {
    BackHandler { onBack() }

    AndroidView(
        factory = { context ->
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
                webViewClient = WebViewClient()
                loadUrl("$piBaseUrl#$pageName")
            }
        },
        modifier = Modifier.fillMaxSize(),
    )
}
