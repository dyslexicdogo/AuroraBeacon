package com.aurorabeacon.data.repository

import com.aurorabeacon.data.api.noaa.KpForecastResponse
import com.aurorabeacon.data.mapper.toDomainSlots
import com.aurorabeacon.domain.model.KpForecastSlot
import com.aurorabeacon.domain.repository.KpForecastRepository
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import kotlin.Result
import kotlin.runCatching

class KpForecastRepositoryImpl(
    private val httpClient: HttpClient
) : KpForecastRepository {

    override suspend fun getGlobalKpForecast(): Result<List<KpForecastSlot>> = runCatching {
        // NOAA SWPC 3-day Kp forecast JSON
        val response: KpForecastResponse = httpClient.get(
            "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
        ).body()

        response.toDomainSlots()
    }
}