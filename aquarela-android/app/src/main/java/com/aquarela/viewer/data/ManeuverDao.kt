package com.aquarela.viewer.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface ManeuverDao {
    @Query("SELECT * FROM maneuvers WHERE session_id = :sessionId ORDER BY entry_time")
    suspend fun forSession(sessionId: Int): List<Maneuver>

    @Insert
    suspend fun insertAll(maneuvers: List<Maneuver>)
}
