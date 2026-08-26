package com.aurorabeacon.domain.repository

import com.aurorabeacon.domain.model.LocalAuroraActivity
import com.aurorabeacon.domain.model.Location
import kotlin.Result

interface LocalAuroraActivityRepository {
    suspend fun getLocalAuroraActivity(
        location: Location
    ): Result<LocalAuroraActivity>
}