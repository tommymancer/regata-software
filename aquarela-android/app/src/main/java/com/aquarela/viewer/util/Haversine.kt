package com.aquarela.viewer.util

import kotlin.math.*

fun haversineNm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val R = 3440.065
    val dLat = Math.toRadians(lat2 - lat1)
    val dLon = Math.toRadians(lon2 - lon1)
    val a = sin(dLat / 2).pow(2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
            sin(dLon / 2).pow(2)
    return 2 * R * asin(sqrt(a))
}
