package com.aurorabeacon.data.mapper

import com.aurorabeacon.data.api.noaa.OvationResponse
import com.aurorabeacon.domain.model.LocalAuroraActivity
import com.aurorabeacon.domain.model.Location
import kotlinx.datetime.Instant

fun OvationResponse.toDomainActivity(
    location: Location,
    fetchTime: Instant
): LocalAuroraActivity {
    // Find nearest grid point to requested location
    val nearest = `data`.minByOrNull { point ->
        val dLat = point.lat - location.latitude
        val dLon = point.lon - location.longitude
        dLat * dLat + dLon * dLon
    }

    val probability = nearest?.probability ?: 0

    return LocalAuroraActivity(
        activityTime = Instant.parse(`forecast_time`),
        activityFetchTime = fetchTime,
        probability = probability.coerceIn(0, 100)
    )
}