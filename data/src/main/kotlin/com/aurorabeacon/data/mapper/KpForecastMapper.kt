package com.aurorabeacon.data.mapper

import com.aurorabeacon.data.api.noaa.KpForecastItem
import com.aurorabeacon.data.api.noaa.KpForecastResponse
import com.aurorabeacon.domain.model.KpForecastSlot
import kotlinx.datetime.Instant

fun KpForecastResponse.toDomainSlots(): List<KpForecastSlot> {
    return `kp-forecast`.map { item ->
        KpForecastSlot(
            timeSlot = Instant.parse(item.time_tag),
            predictedKp = item.kp_index,
            noaaScale = item.noaa_scale,
            isPredicted = item.forecast
        )
    }
}