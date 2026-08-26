package com.aurorabeacon.data.repository

import com.aurorabeacon.data.api.openmeteo.OpenMeteoResponse
import com.aurorabeacon.data.mapper.toDomainSnapshots
import com.aurorabeacon.domain.model.Location
import com.aurorabeacon.domain.model.WeatherSnapshot
import com.aurorabeacon.domain.repository.WeatherRepository
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import kotlinx.coroutines.CancellationException
import kotlinx.datetime.Clock
import kotlinx.datetime.Instant

class WeatherRepositoryImpl(
    private val httpClient: HttpClient
) : WeatherRepository {

    override suspend fun getForecast(
        location: Location,
        startDate: Instant
    ): Result<List<WeatherSnapshot>> {
        return try {
            val fetchTime = Clock.System.now()

            val response: OpenMeteoResponse =
                httpClient.get("https://api.open-meteo.com/v1/forecast") {
                    parameter("latitude", location.latitude)
                    parameter("longitude", location.longitude)
                    parameter("forecast_days", 3)
                    parameter(
                        "hourly",
                        "temperature_2m,dew_point_2m,visibility,cloud_cover_high,cloud_cover_mid,cloud_cover_low"
                    )
                    parameter("timezone", "UTC")
                }.body()

            Result.success(response.hourly.toDomainSnapshots(fetchTime = fetchTime))
        } catch (e: Exception) {
            if (e is CancellationException) throw e
            Result.failure(e)
        }
    }
}