package com.aurorabeacon.domain.repository

import com.aurorabeacon.domain.model.Location
import com.aurorabeacon.domain.model.WeatherSnapshot
import kotlinx.datetime.Instant
import kotlin.Result

interface WeatherRepository {
    suspend fun getForecast(
        location: Location,
        startDate: Instant
    ): Result<List<WeatherSnapshot>>
}