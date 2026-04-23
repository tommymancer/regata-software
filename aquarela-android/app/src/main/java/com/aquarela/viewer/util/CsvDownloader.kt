package com.aquarela.viewer.util

import android.content.ContentValues
import android.content.Context
import android.os.Environment
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

object CsvDownloader {

    /**
     * Download a session CSV from the Pi and save to Downloads folder.
     * Returns the filename on success, null on failure.
     */
    suspend fun download(context: Context, baseUrl: String, csvFilename: String): String? =
        withContext(Dispatchers.IO) {
            // Use applicationContext: the activity may be destroyed before the
            // download finishes; the app context is safe to reference across the
            // process lifetime and avoids leaking the Activity.
            val appCtx = context.applicationContext
            val conn = URL("$baseUrl/api/logs/$csvFilename").openConnection() as HttpURLConnection
            conn.connectTimeout = 10_000
            conn.readTimeout = 30_000
            try {
                if (conn.responseCode != 200) return@withContext null

                val bytes = conn.inputStream.use { it.readBytes() }

                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, csvFilename)
                    put(MediaStore.Downloads.MIME_TYPE, "text/csv")
                    put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                }
                val uri = appCtx.contentResolver.insert(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI, values
                ) ?: return@withContext null

                appCtx.contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
                csvFilename
            } catch (e: Exception) {
                e.printStackTrace()
                null
            } finally {
                // Always release the socket, even on parse/IO/cancellation.
                try { conn.disconnect() } catch (_: Exception) {}
            }
        }
}
