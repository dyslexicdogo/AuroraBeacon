package com.aurorabeacon.data.api.noaa

import kotlinx.serialization.Serializable

@Serializable
data class OvationResponse(
    val `data`: List<OvationPoint>,
    val `observation_time`: String,
    val `forecast_time`: String
)

@Serializable
data class OvationPoint(
    val lat: Double,
    val lon: Double,
    val probability: Int
)