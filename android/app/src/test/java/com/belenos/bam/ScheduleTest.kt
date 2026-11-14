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
        assertFalse(Schedule.prompt(LocalDate.parse("2026-11-14"), Slot.EVENING, emptyList())
            .contains("orders close December 3"))
    }

    @Test fun captionRemovesWrappersAndRejectsGeneratedStoreHours() {
        assertEquals("Send us a message about a custom portrait.", Schedule.caption(
            "Facebook caption: “Send us a message about a custom portrait.”"
        ))
        assertEquals("A photo with a label that reads \"Best dog\".",
            Schedule.caption("A photo with a label that reads \"Best dog\"."))
        assertEquals("Christmas custom orders close December 3. Message us!",
            Schedule.caption("Campaign note: Christmas custom orders close December 3. [Message us!](#)"))
        val prompt = Schedule.prompt(LocalDate.parse("2026-11-14"), Slot.MORNING,
            listOf("Ask about custom 3D prints for your desk today."))
        org.junit.Assert.assertTrue(prompt.contains("Ask about custom 3D prints for"))
        assertFalse(prompt.contains("your desk today"))
        for (hours in listOf("noon to 7 PM", "4 p.m.", "16:30", "12pm")) {
            assertThrows(IllegalArgumentException::class.java) {
                Schedule.caption("Come in at $hours!", "noon–7 PM")
            }
        }
        assertThrows(IllegalArgumentException::class.java) { Schedule.caption("Visit us right now!") }
        assertThrows(IllegalArgumentException::class.java) { Schedule.caption("We're open today.") }
        assertEquals("Visit us today.\n\nToday's hours: noon–7 PM.",
            Schedule.caption("Visit us today.", "noon–7 PM"))
        assertEquals("Ask about a 20 oz tumbler.", Schedule.caption("Ask about a 20 oz tumbler."))
    }

    @Test fun timingDistinguishesDraftTargetFromPostingTime() {
        val day = LocalDate.parse("2026-11-14")
        val saved = Instant.parse("2026-11-14T15:08:00Z")
        val timing = DraftTiming(saved, DraftOrigin.BACKGROUND)
        val draft = Draft(day, Slot.OPENING, "See you in Marion", timing)
        assertEquals("Periodic background check · saved 10:08 AM ET · 8 min after target",
            slotStatus(day, Slot.OPENING, saved, skipped = false, saved = draft))
        assertEquals("Manual catch-up · saved 10:08 AM ET · 8 min after target",
            timing.copy(origin = DraftOrigin.MANUAL).description(day, Slot.OPENING))
        assertEquals("Saved · timing unavailable",
            slotStatus(day, Slot.OPENING, saved, skipped = true, saved = draft.copy(timing = null)))
    }

    @Test fun timingShowsPendingSkippedAndExpiredSlots() {
        val day = LocalDate.parse("2026-11-14")
        val before = Instant.parse("2026-11-14T14:59:59Z")
        val target = Instant.parse("2026-11-14T15:00:00Z")
        val noon = Instant.parse("2026-11-14T17:00:00Z")
        assertEquals("Upcoming", slotStatus(day, Slot.OPENING, before, false, null))
        assertEquals("Due · waiting for draft", slotStatus(day, Slot.OPENING, target, false, null))
        assertEquals("Missed · expired at noon", slotStatus(day, Slot.OPENING, noon, false, null))
        assertEquals("Skipped for this date", slotStatus(day, Slot.OPENING, noon, true, null))
        assertEquals("Due · waiting for draft", slotStatus(day, Slot.MORNING, noon, false, null))
    }
}
