package com.aquarela.viewer.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface TrackPointDao {
    @Query("SELECT * FROM track_points WHERE session_id = :sessionId ORDER BY timestamp")
    suspend fun forSession(sessionId: Int): List<TrackPoint>

    @Insert
    suspend fun insertAll(points: List<TrackPoint>)
}
