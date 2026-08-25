package com.aurorabeacon.data.api.openmeteo

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OpenMeteoDto(
    @SerialName("current")
    val current: CurrentData
)

@Serializable
data class CurrentData(
    @SerialName("time")
    val time: String,
    @SerialName("temperature_2m")
    val temperature: Double,
    @SerialName("cloud_cover")
    val cloudCover: Int,
    @SerialName("visibility")
    val visibility: Double
)
