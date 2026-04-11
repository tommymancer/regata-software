package com.aquarela.viewer.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "sessions")
data class Session(
    @PrimaryKey val id: Int,
    val start_time: String,
    val end_time: String,
    val session_type: String,
    val notes: String? = null,
    val duration_secs: Int = 0,
    val distance_nm: Double = 0.0,
    val avg_bsp_kt: Double = 0.0,
    val max_bsp_kt: Double = 0.0,
    val avg_tws_kt: Double = 0.0,
    val avg_vmg_kt: Double = 0.0,
    val avg_vmc_kt: Double? = null,
    val synced_at: String = "",
    val csv_file: String? = null,
)
