package com.aquarela.viewer.sync

import android.util.Log
import androidx.room.withTransaction
import com.aquarela.viewer.data.AppDatabase
import com.aquarela.viewer.data.Maneuver
import com.aquarela.viewer.data.Session
import com.aquarela.viewer.util.parseCsv
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

private const val TAG = "AquarelaSync"

class SyncManager(private val db: AppDatabase) {

    suspend fun sync(baseUrl: String): Int = withContext(Dispatchers.IO) {
        try {
            val sessionsJson = httpGet("$baseUrl/api/sessions?limit=200")
            val arr = JSONArray(sessionsJson)
            val existing = db.sessionDao().allSessionIds().toSet()
            var synced = 0

            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                val id = obj.getInt("id")
                val endTime = obj.optString("end_time", "")
                val csvFile = obj.optString("csv_file", "")

                if (endTime.isBlank() || csvFile.isBlank() || id in existing) continue

                try {
                    syncSession(baseUrl, id, obj)
                    synced++
                } catch (e: Exception) {
                    Log.w(TAG, "Failed to sync session $id: ${e.message}")
                }
            }
            Log.d(TAG, "Sync complete: $synced new sessions")
            synced
        } catch (e: Exception) {
            Log.e(TAG, "Sync failed: ${e.message}")
            0
        }
    }

    private suspend fun syncSession(baseUrl: String, id: Int, meta: JSONObject) {
        val csvFile = meta.getString("csv_file")
        val filename = csvFile.substringAfterLast("/")

        val csvText = httpGet("$baseUrl/api/logs/$filename")
        val parsed = parseCsv(id, csvText)
        if (parsed.trackPoints.isEmpty()) return

        val maneuversJson = httpGet("$baseUrl/api/sessions/$id/maneuvers")
        val manArr = JSONArray(maneuversJson)
        val maneuvers = (0 until manArr.length()).map { i ->
            val m = manArr.getJSONObject(i)
            Maneuver(
                session_id = id,
                maneuver_type = m.optString("maneuver_type", ""),
                entry_time = m.optString("wall_time", ""),
                lat = m.optDouble("lat", 0.0),
                lon = m.optDouble("lon", 0.0),
                bsp_before = m.optDouble("bsp_before", 0.0),
                bsp_min = m.optDouble("bsp_min", 0.0),
                bsp_after = m.optDouble("bsp_after", 0.0),
                recovery_secs = m.optDouble("recovery_secs", 0.0),
                vmg_before = m.optDouble("vmg_before", 0.0),
                vmg_loss_nm = m.optDouble("vmg_loss_nm", 0.0),
                vmc_before = if (m.isNull("vmc_before")) null else m.optDouble("vmc_before"),
                vmc_loss_nm = if (m.isNull("vmc_loss_nm")) null else m.optDouble("vmc_loss_nm"),
                hdg_before = m.optDouble("hdg_before", 0.0),
                hdg_after = m.optDouble("hdg_after", 0.0),
            )
        }

        val now = java.time.Instant.now().toString()
        val session = Session(
            id = id,
            start_time = meta.optString("start_time", ""),
            end_time = meta.optString("end_time", ""),
            session_type = meta.optString("session_type", "training"),
            notes = meta.optString("notes", null),
            duration_secs = parsed.durationSecs,
            distance_nm = parsed.distanceNm,
            avg_bsp_kt = parsed.avgBspKt,
            max_bsp_kt = parsed.maxBspKt,
            avg_tws_kt = parsed.avgTwsKt,
            avg_vmg_kt = parsed.avgVmgKt,
            avg_vmc_kt = parsed.avgVmcKt,
            synced_at = now,
            csv_file = filename,
        )

        db.withTransaction {
            db.sessionDao().insert(session)
            db.trackPointDao().insertAll(parsed.trackPoints)
            if (maneuvers.isNotEmpty()) db.maneuverDao().insertAll(maneuvers)
        }

        Log.d(TAG, "Synced session $id: ${parsed.trackPoints.size} points, ${maneuvers.size} maneuvers")
    }

    private fun httpGet(url: String): String {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 10_000
        conn.readTimeout = 30_000
        conn.requestMethod = "GET"
        return try {
            if (conn.responseCode != 200) throw Exception("HTTP ${conn.responseCode}")
            conn.inputStream.bufferedReader().readText()
        } finally {
            conn.disconnect()
        }
    }
}
