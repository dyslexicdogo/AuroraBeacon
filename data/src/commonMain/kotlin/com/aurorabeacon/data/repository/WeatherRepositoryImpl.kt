package com.aurorabeacon.data.repository

import com.aurorabeacon.data.api.openmeteo.OpenMeteoDto
import com.aurorabeacon.data.mapper.toDomain
import com.aurorabeacon.domain.model.Location
import com.aurorabeacon.domain.model.WeatherSnapshot
import com.aurorabeacon.domain.repository.WeatherRepository
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.request.*

class WeatherRepositoryImpl(
    private val httpClient: HttpClient
) : WeatherRepository {
    override suspend fun getWeatherData(location: Location): Result<WeatherSnapshot> {
        return try {
            val response: OpenMeteoDto = httpClient.get("https://api.open-meteo.com/v1/forecast") {
                parameter("latitude", location.latitude)
                parameter("longitude", location.longitude)
                parameter("current", "temperature_2m,cloud_cover,visibility")
            }.body()
            Result.success(response.toDomain())
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
