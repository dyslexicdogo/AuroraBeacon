package com.aurorabeacon.domain.model

data class Location(
    val latitude: Double,
    val longitude: Double,
    val name: String? = null
)
