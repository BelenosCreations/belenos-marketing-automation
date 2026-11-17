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
    MANUAL("Generated manually"),
    TEST("Test run"),
    UNKNOWN("Draft check")
}

data class DraftReview(
    val contentNeeded: String = "",
    val imagePrompt: String = "",
    val approved: Boolean = false,
    val revision: Long = 0,
    val imageId: String? = null
)

data class Draft(
    val day: LocalDate,
    val slot: Slot,
    val caption: String,
    val timing: DraftTiming? = null,
    val review: DraftReview = DraftReview()
) {
    val postingTime: LocalTime? get() = timing?.postingTimeOverride ?: slot.draftTime
}

data class DraftTiming(val savedAt: Instant, val origin: DraftOrigin,
                       val postingTimeOverride: LocalTime? = null) {
    fun description(day: LocalDate, slot: Slot): String {
        val localTime = savedAt.atZone(Schedule.eastern).format(clockFormat)
        val postTime = postingTimeOverride ?: slot.draftTime ?: return "${origin.label} · saved $localTime ET"
        val target = day.atTime(postTime).atZone(Schedule.eastern).toInstant()
        val delay = Duration.between(target, savedAt).toMinutes()
        val early = Duration.between(savedAt, target).toMinutes()
        val timing = when {
            savedAt < target -> "$early min before posting"
            delay == 0L -> "at posting time"
            else -> "$delay min after posting time"
        }
        return "${origin.label} · saved $localTime ET · $timing"
    }

    companion object {
        private val clockFormat = DateTimeFormatter.ofPattern("h:mm a", Locale.US)
    }
}

fun slotStatus(day: LocalDate, slot: Slot, now: Instant, skipped: Boolean, saved: Draft?,
               postingTime: LocalTime? = slot.draftTime): String {
    if (saved != null) return saved.timing?.description(day, slot) ?: "Saved · timing unavailable"
    if (skipped) return "Skipped for this date"
    val clock = now.atZone(Schedule.eastern).toLocalTime()
    if (now < day.atTime(checkNotNull(postingTime)).atZone(Schedule.eastern).toInstant()) return "Upcoming"
    if (slot == Slot.OPENING && clock >= LocalTime.NOON) return "Missed · expired at noon"
    return "Due · waiting for draft"
}
