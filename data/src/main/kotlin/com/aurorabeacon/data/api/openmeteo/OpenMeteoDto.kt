package com.aurorabeacon.data.api.openmeteo

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OpenMeteoResponse(
    val hourly: HourlyData
)

@Serializable
data class HourlyData(
    val time: List<String>,
    @SerialName("temperature_2m") val temperature: List<Double>,
    @SerialName("dew_point_2m") val dewPoint: List<Double>,
    val visibility: List<Double>,
    @SerialName("cloud_cover_high") val cloudHigh: List<Int>,
    @SerialName("cloud_cover_mid") val cloudMid: List<Int>,
    @SerialName("cloud_cover_low") val cloudLow: List<Int>
)