package com.aquarela.viewer.util

import com.aquarela.viewer.data.TrackPoint
import kotlin.math.abs
import kotlin.math.cos

data class ParsedSession(
    val trackPoints: List<TrackPoint>,
    val durationSecs: Int,
    val distanceNm: Double,
    val avgBspKt: Double,
    val maxBspKt: Double,
    val avgTwsKt: Double,
    val avgVmgKt: Double,
    val avgVmcKt: Double?,
)

fun parseCsv(sessionId: Int, csvText: String): ParsedSession {
    val lines = csvText.lines().filter { it.isNotBlank() }
    if (lines.size < 2) return ParsedSession(emptyList(), 0, 0.0, 0.0, 0.0, 0.0, 0.0, null)

    val header = lines[0].split(",")
    val colIndex = header.withIndex().associate { (i, name) -> name.trim() to i }

    fun col(row: List<String>, name: String): String? {
        val idx = colIndex[name] ?: return null
        return row.getOrNull(idx)?.takeIf { it.isNotBlank() }
    }

    fun colDouble(row: List<String>, name: String): Double? = col(row, name)?.toDoubleOrNull()

    val points = mutableListOf<TrackPoint>()

    for (i in 1 until lines.size) {
        val cols = lines[i].split(",")
        val lat = colDouble(cols, "Lat") ?: continue
        val lon = colDouble(cols, "Lon") ?: continue
        val ts = col(cols, "Timestamp") ?: continue

        points.add(TrackPoint(
            session_id = sessionId,
            timestamp = ts,
            lat = lat, lon = lon,
            bsp_kt = colDouble(cols, "BSP") ?: 0.0,
            sog_kt = colDouble(cols, "SOG") ?: 0.0,
            cog_deg = colDouble(cols, "COG") ?: 0.0,
            perf_pct = colDouble(cols, "Perf"),
            hdg_deg = colDouble(cols, "Heading") ?: 0.0,
            twa_deg = colDouble(cols, "TWA") ?: 0.0,
            tws_kt = colDouble(cols, "TWS") ?: 0.0,
            brg_deg = colDouble(cols, "BRG"),
        ))
    }

    if (points.isEmpty()) return ParsedSession(emptyList(), 0, 0.0, 0.0, 0.0, 0.0, 0.0, null)

    val durationSecs = parseDurationSecs(points.first().timestamp, points.last().timestamp)

    var distanceNm = 0.0
    for (i in 1 until points.size) {
        distanceNm += haversineNm(points[i - 1].lat, points[i - 1].lon, points[i].lat, points[i].lon)
    }

    val avgBsp = points.map { it.bsp_kt }.average()
    val maxBsp = points.maxOf { it.bsp_kt }
    val avgTws = points.map { it.tws_kt }.average()

    val vmgs = points.filter { it.twa_deg != 0.0 }
        .map { abs(it.bsp_kt * cos(Math.toRadians(it.twa_deg))) }
    val avgVmg = if (vmgs.isNotEmpty()) vmgs.average() else 0.0

    val vmcPoints = points.filter { it.brg_deg != null }
    val avgVmc = if (vmcPoints.isNotEmpty()) {
        vmcPoints.map { pt -> pt.sog_kt * cos(Math.toRadians(pt.cog_deg - pt.brg_deg!!)) }.average()
    } else null

    return ParsedSession(points, durationSecs, distanceNm, avgBsp, maxBsp, avgTws, avgVmg, avgVmc)
}

private fun parseDurationSecs(first: String, last: String): Int {
    return try {
        val fmt = java.time.format.DateTimeFormatter.ISO_DATE_TIME
        val t1 = java.time.Instant.from(fmt.parse(first))
        val t2 = java.time.Instant.from(fmt.parse(last))
        java.time.Duration.between(t1, t2).seconds.toInt()
    } catch (e: Exception) { 0 }
}
