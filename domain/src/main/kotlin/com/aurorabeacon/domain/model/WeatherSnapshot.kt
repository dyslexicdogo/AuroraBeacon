package com.aurorabeacon.domain.model

import kotlinx.serialization.Serializable

@Serializable
data class WeatherSnapshot(
    val forecastTime: kotlinx.datetime.Instant,
    val forecastFetchTime: kotlinx.datetime.Instant,
    val cloudHigh: Int,
    val cloudMid: Int,
    val cloudLow: Int,
    val visibility: Double,
    val temperature: Double,
    val dewPoint: Double
)