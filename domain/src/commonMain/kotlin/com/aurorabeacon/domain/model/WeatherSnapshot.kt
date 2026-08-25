package com.aurorabeacon.domain.model

import kotlinx.datetime.LocalDateTime

data class WeatherSnapshot(
    val temperature: Double,
    val cloudCover: Int, // Percentage
    val visibility: Int, // Meters
    val timestamp: LocalDateTime
)
