package com.aurorabeacon.data.repository

import com.aurorabeacon.domain.model.Location
import com.aurorabeacon.domain.model.SunMoonPosition
import com.aurorabeacon.domain.repository.SunMoonRepository
import kotlinx.datetime.Instant
import kotlinx.datetime.toJavaInstant
import org.shredzone.commons.suncalc.MoonIllumination
import org.shredzone.commons.suncalc.MoonPosition
import org.shredzone.commons.suncalc.SunPosition
import kotlin.Result
import kotlin.time.Duration.Companion.hours

class SunMoonRepositoryImpl : SunMoonRepository {

    override suspend fun getSunMoonPositions(
        location: Location,
        startDate: Instant
    ): Result<List<SunMoonPosition>> = kotlin.runCatching {
        val results = mutableListOf<SunMoonPosition>()

        // Generate positions for next 72 hours (3 days) at 1-hour intervals for consistency
        for (hourOffset in 0..72) {
            val time = startDate.plus(hourOffset.hours)
            val pos = calculateSunMoon(time, location)
            results.add(pos)
        }

        results
    }

    private fun calculateSunMoon(time: Instant, location: Location): SunMoonPosition {
        val javaInstant = time.toJavaInstant()
        
        // Use shredzone suncalc for efficient, reliable local calculations
        val sunPos = SunPosition.compute()
            .on(javaInstant)
            .at(location.latitude, location.longitude)
            .execute()

        val moonPos = MoonPosition.compute()
            .on(javaInstant)
            .at(location.latitude, location.longitude)
            .execute()

        val moonIllum = MoonIllumination.compute()
            .on(javaInstant)
            .execute()

        return SunMoonPosition(
            positionTime = time,
            sunAltitude = sunPos.altitude,
            moonAltitude = moonPos.altitude,
            moonIllumination = moonIllum.fraction * 100.0,
            moonAzimuth = moonPos.azimuth
        )
    }
}
