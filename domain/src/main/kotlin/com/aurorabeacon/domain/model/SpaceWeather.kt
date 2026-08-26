package com.aurorabeacon.domain.model

import kotlinx.datetime.Instant
import kotlinx.serialization.Serializable

@Serializable
data class KpForecastSlot(
    val timeSlot: Instant,
    val predictedKp: Double,
    val noaaScale: String? = null,
    val isPredicted: Boolean
)

@Serializable
data class LocalAuroraActivity(
    val activityTime: Instant,
    val activityFetchTime: Instant,
    val probability: Int  // 0-100
)

@Serializable
data class SunMoonPosition(
    val positionTime: Instant,
    val sunAltitude: Double,
    val moonAltitude: Double,
    val moonIllumination: Double,
    val moonAzimuth: Double
)
