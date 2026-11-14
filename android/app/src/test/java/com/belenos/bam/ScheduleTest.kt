package com.belenos.bam

import java.time.Instant
import java.time.LocalDate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Test

class ScheduleTest {
    private val confirmed = LocalDate.parse("2026-12-10")

    private fun due(at: String, through: LocalDate = confirmed) =
        Schedule.due(Instant.parse(at), through)

    @Test fun keepsEasternTimesAndOpeningCutoff() {
        assertEquals(emptyList<Slot>(), due("2026-11-14T14:59:59Z"))
        assertEquals(listOf(Slot.MORNING, Slot.OPENING), due("2026-11-14T15:00:00Z"))
        assertEquals(listOf(Slot.MORNING), due("2026-11-14T17:00:00Z"))
        assertEquals(listOf(Slot.MORNING, Slot.EVENING), due("2026-11-14T23:30:00Z"))
        assertEquals(listOf(Slot.MORNING, Slot.OPENING),
            due("2027-07-03T14:00:00Z", LocalDate.parse("2027-07-03")))
    }

    @Test fun respectsExceptionsAndConfirmedHours() {
        assertEquals(listOf(Slot.EVENING), due("2026-11-16T23:30:00Z"))
        assertEquals(listOf(Slot.MORNING), due("2026-11-17T23:30:00Z"))
        assertEquals(listOf(Slot.MORNING), due("2026-11-26T15:00:00Z"))
        assertEquals(listOf(Slot.MORNING),
            due("2027-01-07T15:00:00Z", LocalDate.parse("2027-01-07")))
        assertEquals(listOf(Slot.MORNING), due("2027-01-08T15:00:00Z"))
    }

    @Test fun campaignOverridesOnlyTheSelectedDatesDrafts() {
        val day = LocalDate.parse("2026-11-14")
        val instant = Instant.parse("2026-11-14T15:00:00Z")
        val campaign = Campaign("Pet memorial portraits", "Can combine separate photos",
            setOf(Slot.OPENING))
        assertEquals(listOf(Slot.MORNING), Schedule.due(instant, confirmed, campaign))
        val prompt = Schedule.prompt(day, Slot.MORNING, emptyList(), campaign)
        org.junit.Assert.assertTrue(prompt.contains("Campaign topic: Pet memorial portraits"))
        org.junit.Assert.assertTrue(prompt.contains("Owner-confirmed facts: Can combine separate photos"))
        assertFalse(Schedule.prompt(day.plusDays(1), Slot.MORNING, emptyList())
            .contains("Can combine separate photos"))
        assertThrows(IllegalArgumentException::class.java) { Campaign(skipped = setOf(Slot.SAMPLE)) }
    }

    @Test fun captionChecksBrandAndAddsConfirmedHours() {
        assertThrows(IllegalArgumentException::class.java) { Schedule.caption("See our bees 🐝") }
        assertThrows(IllegalArgumentException::class.java) { Schedule.caption(" ") }
        assertEquals("Browse our custom gifts.\n\nToday's hours: noon–7 PM.",
            Schedule.caption(" Browse our custom gifts. ", "noon–7 PM"))
        assertFalse(Schedule.prompt(LocalDate.parse("2026-12-04"), Slot.MORNING, emptyList())
            .contains("orders close December 3"))
    }
}
