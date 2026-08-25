package com.aurorabeacon.data.mapper

import com.aurorabeacon.data.api.openmeteo.OpenMeteoDto
import com.aurorabeacon.domain.model.WeatherSnapshot
import kotlinx.datetime.LocalDateTime

fun OpenMeteoDto.toDomain(): WeatherSnapshot {
    return WeatherSnapshot(
        temperature = current.temperature,
        cloudCover = current.cloudCover,
        visibility = current.visibility.toInt(),
        timestamp = LocalDateTime.parse(current.time)
    )
}
