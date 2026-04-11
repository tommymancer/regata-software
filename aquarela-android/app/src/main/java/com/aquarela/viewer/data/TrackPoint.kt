package com.aquarela.viewer.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "track_points",
    foreignKeys = [ForeignKey(
        entity = Session::class,
        parentColumns = ["id"],
        childColumns = ["session_id"],
        onDelete = ForeignKey.CASCADE,
    )],
    indices = [Index("session_id")],
)
data class TrackPoint(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val session_id: Int,
    val timestamp: String,
    val lat: Double,
    val lon: Double,
    val bsp_kt: Double = 0.0,
    val sog_kt: Double = 0.0,
    val cog_deg: Double = 0.0,
    val perf_pct: Double? = null,
    val hdg_deg: Double = 0.0,
    val twa_deg: Double = 0.0,
    val tws_kt: Double = 0.0,
    val brg_deg: Double? = null,
)
