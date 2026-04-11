package com.aquarela.viewer.sessions

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.aquarela.viewer.data.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class SessionDetail(
    val session: Session,
    val trackPoints: List<TrackPoint>,
    val maneuvers: List<Maneuver>,
)

class SessionDetailViewModel(app: Application) : AndroidViewModel(app) {
    private val db = AppDatabase.get(app)
    private val _detail = MutableStateFlow<SessionDetail?>(null)
    val detail: StateFlow<SessionDetail?> = _detail

    fun load(sessionId: Int) {
        viewModelScope.launch {
            val session = db.sessionDao().getById(sessionId) ?: return@launch
            val points = db.trackPointDao().forSession(sessionId)
            val maneuvers = db.maneuverDao().forSession(sessionId)
            _detail.value = SessionDetail(session, points, maneuvers)
        }
    }
}
