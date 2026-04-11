package com.aquarela.viewer.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "maneuvers",
    foreignKeys = [ForeignKey(
        entity = Session::class,
        parentColumns = ["id"],
        childColumns = ["session_id"],
        onDelete = ForeignKey.CASCADE,
    )],
    indices = [Index("session_id")],
)
data class Maneuver(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val session_id: Int,
    val maneuver_type: String,
    val entry_time: String,
    val lat: Double = 0.0,
    val lon: Double = 0.0,
    val bsp_before: Double = 0.0,
    val bsp_min: Double = 0.0,
    val bsp_after: Double = 0.0,
    val recovery_secs: Double = 0.0,
    val vmg_before: Double = 0.0,
    val vmg_loss_nm: Double = 0.0,
    val vmc_before: Double? = null,
    val vmc_loss_nm: Double? = null,
    val hdg_before: Double = 0.0,
    val hdg_after: Double = 0.0,
)
