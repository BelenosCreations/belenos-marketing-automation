package com.belenos.bam

import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.util.Locale

enum class DraftOrigin(val label: String) {
    BACKGROUND("Periodic background check"),
    APP_OPEN("App catch-up"),
    MANUAL("Manual catch-up"),
    TEST("Test run"),
    UNKNOWN("Draft check")
}

data class Draft(val day: LocalDate, val slot: Slot, val caption: String, val timing: DraftTiming? = null)

data class DraftTiming(val savedAt: Instant, val origin: DraftOrigin) {
    fun description(day: LocalDate, slot: Slot): String {
        val localTime = savedAt.atZone(Schedule.eastern).format(clockFormat)
        val draftTime = slot.draftTime ?: return "${origin.label} · saved $localTime ET"
        val target = day.atTime(draftTime).atZone(Schedule.eastern).toInstant()
        val delay = Duration.between(target, savedAt).toMinutes()
        val timing = when {
            savedAt < target -> "before target"
            delay == 0L -> "within 1 min of target"
            else -> "$delay min after target"
        }
        return "${origin.label} · saved $localTime ET · $timing"
    }

    companion object {
        private val clockFormat = DateTimeFormatter.ofPattern("h:mm a", Locale.US)
    }
}

fun slotStatus(day: LocalDate, slot: Slot, now: Instant, skipped: Boolean, saved: Draft?): String {
    if (saved != null) return saved.timing?.description(day, slot) ?: "Saved · timing unavailable"
    if (skipped) return "Skipped for this date"
    val clock = now.atZone(Schedule.eastern).toLocalTime()
    if (clock < checkNotNull(slot.draftTime)) return "Upcoming"
    if (slot == Slot.OPENING && clock >= LocalTime.NOON) return "Missed · expired at noon"
    return "Due · waiting for draft"
}
