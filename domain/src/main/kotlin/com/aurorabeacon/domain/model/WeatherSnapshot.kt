package com.aurorabeacon.domain.model

import kotlinx.serialization.Serializable
import kotlinx.datetime.Instant

@Serializable
data class WeatherSnapshot(
    val forecastTime: Instant,
    val forecastFetchTime: Instant,
    val cloudHigh: Int,
    val cloudMid: Int,
    val cloudLow: Int,
    val visibility: Double,
    val temperature: Double,
    val dewPoint: Double
)