package com.aquarela.viewer.sessions

import android.graphics.Color
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import com.aquarela.viewer.data.Maneuver
import com.aquarela.viewer.data.TrackPoint
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.BoundingBox
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polyline

private const val MAX_RENDER_POINTS = 5000

@Composable
fun TrackMapView(
    trackPoints: List<TrackPoint>,
    maneuvers: List<Maneuver>,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current

    val displayPoints = remember(trackPoints) {
        if (trackPoints.size <= MAX_RENDER_POINTS) trackPoints
        else {
            val step = trackPoints.size / MAX_RENDER_POINTS + 1
            trackPoints.filterIndexed { i, _ -> i % step == 0 }
        }
    }

    AndroidView(
        factory = { ctx ->
            Configuration.getInstance().userAgentValue = ctx.packageName
            MapView(ctx).apply {
                setTileSource(TileSourceFactory.MAPNIK)
                setMultiTouchControls(true)
                minZoomLevel = 8.0
                maxZoomLevel = 18.0
            }
        },
        modifier = modifier,
        update = { mapView ->
            mapView.overlays.clear()
            if (displayPoints.isEmpty()) return@AndroidView

            // Draw track colored by performance
            var segStart = 0
            while (segStart < displayPoints.size - 1) {
                val perf = displayPoints[segStart].perf_pct
                val color = perfColor(perf)
                val segment = Polyline()
                segment.outlinePaint.color = color
                segment.outlinePaint.strokeWidth = 6f

                var i = segStart
                while (i < displayPoints.size) {
                    val pt = displayPoints[i]
                    segment.addPoint(GeoPoint(pt.lat, pt.lon))
                    if (i > segStart && perfColor(pt.perf_pct) != color) break
                    i++
                }
                mapView.overlays.add(segment)
                segStart = (i - 1).coerceAtLeast(segStart + 1)
            }

            // Maneuver markers
            for (m in maneuvers) {
                val marker = Marker(mapView)
                marker.position = GeoPoint(m.lat, m.lon)
                marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                val type = if (m.maneuver_type == "tack") "Virata" else "Strambata"
                val meters = m.vmg_loss_nm * 1852
                marker.title = "%s — %.0f m persi".format(type, meters)
                mapView.overlays.add(marker)
            }

            // Zoom to fit — post to ensure MapView has been laid out
            val lats = displayPoints.map { it.lat }
            val lons = displayPoints.map { it.lon }
            val bb = BoundingBox(lats.max(), lons.max(), lats.min(), lons.min())
            mapView.post {
                mapView.zoomToBoundingBox(bb.increaseByScale(1.3f), true)
                mapView.invalidate()
            }
        },
    )
}

private fun perfColor(perf: Double?): Int {
    if (perf == null) return Color.GRAY
    return when {
        perf >= 90.0 -> Color.parseColor("#4CAF50")
        perf >= 70.0 -> Color.parseColor("#FFC107")
        else -> Color.parseColor("#FF5722")
    }
}
