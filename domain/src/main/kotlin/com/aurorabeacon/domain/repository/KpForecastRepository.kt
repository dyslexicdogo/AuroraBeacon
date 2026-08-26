package com.aurorabeacon.domain.repository

import com.aurorabeacon.domain.model.KpForecastSlot
import kotlin.Result

interface KpForecastRepository {
    // No Location — Kp/Bz are global planetary scalars
    suspend fun getGlobalKpForecast(): Result<List<KpForecastSlot>>
}