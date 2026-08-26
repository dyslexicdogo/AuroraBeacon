package com.aurorabeacon.data.mapper

import com.aurorabeacon.data.api.openmeteo.HourlyData
import com.aurorabeacon.domain.model.WeatherSnapshot
import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.Instant
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toInstant

fun HourlyData.toDomainSnapshots(
    fetchTime: Instant
): List<WeatherSnapshot> {
    return time.mapIndexed { index, timeString ->
        WeatherSnapshot(
            forecastTime = LocalDateTime.parse(timeString).toInstant(TimeZone.UTC),
            temperature = temperature[index],
            dewPoint = dewPoint[index],
            visibility = visibility[index] / 1000.0,  // meters → km
            cloudHigh = cloudHigh[index],
            cloudMid = cloudMid[index],
            cloudLow = cloudLow[index],
            forecastFetchTime = fetchTime
        )
    }
}