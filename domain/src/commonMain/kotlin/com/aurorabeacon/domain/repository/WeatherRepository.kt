package com.aurorabeacon.domain.repository

import com.aurorabeacon.domain.model.Location
import com.aurorabeacon.domain.model.WeatherSnapshot

interface WeatherRepository {
    suspend fun getWeatherData(location: Location): Result<WeatherSnapshot>
}
