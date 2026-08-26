package com.aurorabeacon.data.repository

import com.aurorabeacon.data.api.noaa.OvationResponse
import com.aurorabeacon.data.mapper.toDomainActivity
import com.aurorabeacon.domain.model.LocalAuroraActivity
import com.aurorabeacon.domain.model.Location
import com.aurorabeacon.domain.repository.LocalAuroraActivityRepository
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import kotlinx.datetime.Instant
import kotlinx.datetime.Clock
import kotlin.Result
import kotlin.runCatching

class LocalAuroraActivityRepositoryImpl(
    private val httpClient: HttpClient
) : LocalAuroraActivityRepository {

    override suspend fun getLocalAuroraActivity(
        location: Location
    ): Result<LocalAuroraActivity> = runCatching {
        val fetchTime = Clock.System.now()

        // NOAA OVATION model - northern hemisphere
        val response: OvationResponse = httpClient.get(
            "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"
        ).body()

        response.toDomainActivity(location, fetchTime)
    }
}