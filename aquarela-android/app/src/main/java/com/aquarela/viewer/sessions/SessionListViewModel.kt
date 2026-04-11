package com.aquarela.viewer.sessions

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import com.aquarela.viewer.data.AppDatabase
import com.aquarela.viewer.data.Session
import kotlinx.coroutines.flow.Flow

class SessionListViewModel(app: Application) : AndroidViewModel(app) {
    private val db = AppDatabase.get(app)
    val sessions: Flow<List<Session>> = db.sessionDao().allSessions()
}
