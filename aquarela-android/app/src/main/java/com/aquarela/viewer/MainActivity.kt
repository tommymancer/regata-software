package com.aquarela.viewer

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.aquarela.viewer.data.AppDatabase
import com.aquarela.viewer.live.LiveTab
import com.aquarela.viewer.sessions.SessionDetailScreen
import com.aquarela.viewer.sessions.SessionListScreen
import com.aquarela.viewer.settings.SettingsScreen
import com.aquarela.viewer.sync.SyncManager
import kotlinx.coroutines.launch
import org.osmdroid.config.Configuration

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Configuration.getInstance().load(this, getSharedPreferences("osmdroid", MODE_PRIVATE))
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                AquarelaApp()
            }
        }
    }

    @Composable
    private fun AquarelaApp() {
        val navController = rememberNavController()
        var selectedTab by remember { mutableIntStateOf(0) }
        var piBaseUrl by remember { mutableStateOf<String?>(null) }
        val scope = rememberCoroutineScope()
        val db = remember { AppDatabase.get(this@MainActivity) }
        val syncManager = remember { SyncManager(db) }

        Scaffold(
            bottomBar = {
                NavigationBar {
                    NavigationBarItem(
                        selected = selectedTab == 0,
                        onClick = {
                            selectedTab = 0
                            navController.navigate("live") { popUpTo("live") { inclusive = true } }
                        },
                        icon = { Icon(Icons.Default.PlayArrow, "Live") },
                        label = { Text("Live") },
                    )
                    NavigationBarItem(
                        selected = selectedTab == 1,
                        onClick = {
                            selectedTab = 1
                            navController.navigate("sessions") { popUpTo("sessions") { inclusive = true } }
                        },
                        icon = { Icon(Icons.Default.DateRange, "Sessioni") },
                        label = { Text("Sessioni") },
                    )
                    NavigationBarItem(
                        selected = selectedTab == 2,
                        onClick = {
                            selectedTab = 2
                            navController.navigate("settings") { popUpTo("settings") { inclusive = true } }
                        },
                        icon = { Icon(Icons.Default.Settings, "Impostazioni") },
                        label = { Text("Impostazioni") },
                    )
                }
            },
        ) { padding ->
            NavHost(navController, startDestination = "live", modifier = Modifier.padding(padding)) {
                composable("live") {
                    LiveTab(onPiFound = { url ->
                        piBaseUrl = url
                        scope.launch {
                            val count = syncManager.sync(url)
                            if (count > 0) {
                                runOnUiThread {
                                    Toast.makeText(this@MainActivity, "$count sessioni sincronizzate", Toast.LENGTH_SHORT).show()
                                }
                            }
                        }
                    })
                }
                composable("sessions") {
                    SessionListScreen(onSessionClick = { id -> navController.navigate("session/$id") })
                }
                composable(
                    "session/{id}",
                    arguments = listOf(navArgument("id") { type = NavType.IntType }),
                ) { backStack ->
                    val id = backStack.arguments!!.getInt("id")
                    SessionDetailScreen(sessionId = id, piBaseUrl = piBaseUrl, onBack = { navController.popBackStack() })
                }
                composable("settings") {
                    SettingsScreen(piBaseUrl = piBaseUrl)
                }
            }
        }
    }
}
