package com.aurorabeacon.data.api.noaa

import kotlinx.serialization.Serializable

@Serializable
data class KpForecastResponse(
    val `kp-forecast`: List<KpForecastItem>
)

@Serializable
data class KpForecastItem(
    val time_tag: String,
    val kp_index: Double,
    val noaa_scale: String? = null,
    val forecast: Boolean
)