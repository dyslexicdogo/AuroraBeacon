package com.aurorabeacon.domain.repository

import com.aurorabeacon.domain.model.Location
import com.aurorabeacon.domain.model.SunMoonPosition
import kotlinx.datetime.Instant
import kotlin.Result

interface SunMoonRepository {
    suspend fun getSunMoonPositions(
        location: Location,
        startDate: Instant
    ): Result<List<SunMoonPosition>>
}