package com.aquarela.viewer.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface SessionDao {
    @Query("SELECT * FROM sessions ORDER BY start_time DESC")
    fun allSessions(): Flow<List<Session>>

    @Query("SELECT id FROM sessions")
    suspend fun allSessionIds(): List<Int>

    @Query("SELECT * FROM sessions WHERE id = :id")
    suspend fun getById(id: Int): Session?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(session: Session)
}
