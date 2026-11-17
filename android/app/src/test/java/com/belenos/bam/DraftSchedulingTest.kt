package com.belenos.bam

import android.content.Context
import androidx.work.Configuration
import androidx.work.ListenableWorker
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.WorkerFactory
import androidx.work.WorkerParameters
import androidx.work.testing.SynchronousExecutor
import androidx.work.testing.WorkManagerTestInitHelper
import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalTime
import java.time.LocalDate
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class DraftSchedulingTest {
    private val day = LocalDate.parse("2026-11-14")
    private var now = Instant.parse("2026-11-14T14:59:00Z")
    private var generated = 0
    private lateinit var context: Context
    private lateinit var manager: WorkManager

    @Before fun setUp() {
        context = RuntimeEnvironment.getApplication()
        context.deleteDatabase("drafts.db")
        context.getSharedPreferences("bam", Context.MODE_PRIVATE).edit()
            .clear().putInt("lead_minutes", 0).commit()
        val factory = object : WorkerFactory() {
            override fun createWorker(appContext: Context, workerClassName: String,
                workerParameters: WorkerParameters): ListenableWorker? {
                if (workerClassName != DraftWorker::class.java.name) return null
                return DraftWorker(appContext, workerParameters, { now }, { true }) { consume ->
                    consume {
                        generated++
                        "Ask us about custom gifts."
                    }
                }
            }
        }
        val executor = SynchronousExecutor()
        val config = Configuration.Builder().setExecutor(executor).setTaskExecutor(executor)
            .setWorkerFactory(factory).build()
        WorkManagerTestInitHelper.initializeTestWorkManager(context, config)
        manager = WorkManager.getInstance(context)
    }

    @After fun tearDown() = WorkManagerTestInitHelper.closeWorkDatabase()

    @Test fun periodicWorkFillsMorningAndEveningSlotsAndPreservesTheMorningEdit() {
        setEnabled(true)
        DraftStore(context).use { it.saveCampaign(day, Campaign(skipped = setOf(Slot.OPENING))) }
        DraftWorker.enable(context)
        DraftWorker.enable(context)
        val periodic = workInfo("scheduled-drafts")
        assertEquals(0, generated)

        val driver = checkNotNull(WorkManagerTestInitHelper.getTestDriver(context))
        now = Instant.parse("2026-11-14T15:03:00Z")
        driver.setPeriodDelayMet(periodic.id)
        val morning = DraftStore(context).use { it.recent().single() }
        assertEquals(Slot.MORNING, morning.slot)
        assertEquals(DraftTiming(now, DraftOrigin.BACKGROUND), morning.timing)
        DraftStore(context).use { it.edit(morning, "Owner's morning caption") }

        now = Instant.parse("2026-11-14T23:35:00Z")
        driver.setPeriodDelayMet(periodic.id)
        val drafts = DraftStore(context).use { it.recent().associateBy(Draft::slot) }
        assertEquals(setOf(Slot.MORNING, Slot.EVENING), drafts.keys)
        assertEquals("Owner's morning caption", drafts[Slot.MORNING]?.caption)
        assertEquals(DraftTiming(now, DraftOrigin.BACKGROUND), drafts[Slot.EVENING]?.timing)
        assertEquals(2, generated)
        assertEquals(WorkInfo.State.ENQUEUED, workInfo("scheduled-drafts").state)
    }

    @Test fun pauseCancelsPeriodicWorkAndManualCatchUpStillSavesADraft() {
        setEnabled(true)
        DraftWorker.enable(context)
        setEnabled(false)
        DraftWorker.disable(context)
        assertEquals(WorkInfo.State.CANCELLED, workInfo("scheduled-drafts").state)

        now = Instant.parse("2026-11-14T17:30:00Z")
        DraftWorker.runOnce(context, sample = false)
        assertEquals(0, generated)
        DraftWorker.runOnce(context, sample = false, manual = true)
        assertEquals(WorkInfo.State.SUCCEEDED, workInfo("manual-drafts").state)
        val drafts = DraftStore(context).use { it.recent() }
        assertEquals(setOf(Slot.MORNING, Slot.EVENING), drafts.map { it.slot }.toSet())
        assertEquals(true, drafts.all { it.timing == DraftTiming(now, DraftOrigin.MANUAL) })
    }

    @Test fun automaticLeadTimeGeneratesBeforeTargetAndDoesNotReplaceApprovedDraft() {
        now = Instant.parse("2026-11-14T13:00:00Z") // 8 AM ET
        context.getSharedPreferences("bam", Context.MODE_PRIVATE).edit()
            .putInt("lead_minutes", 120).commit()
        setEnabled(true)
        DraftWorker.runOnce(context, sample = false)
        assertEquals(1, generated)
        DraftStore(context).use { store ->
            val draft = checkNotNull(store.find(day, Slot.MORNING))
            assertEquals(DraftOrigin.APP_OPEN, draft.timing?.origin)
            assertEquals("120 min before posting", draft.timing?.description(day, Slot.MORNING)
                ?.substringAfterLast(" · "))
            assertEquals(true, store.setApproval(draft, true))
        }
        now = Instant.parse("2026-11-14T14:31:00Z") // 9:31 AM ET
        DraftWorker.runOnce(context, sample = false)
        val drafts = DraftStore(context).use { it.recent().associateBy(Draft::slot) }
        assertEquals(2, generated)
        assertEquals(setOf(Slot.MORNING, Slot.OPENING), drafts.keys)
        assertEquals(true, drafts.getValue(Slot.MORNING).review.approved)
    }

    @Test fun manualTodayAndTomorrowGenerateImmediatelyWhileAutomaticIsPaused() {
        now = Instant.parse("2026-11-14T13:00:00Z")
        setEnabled(false)
        val tomorrow = day.plusDays(1)
        DraftWorker.runOnce(context, sample = false, manual = true, targetDay = tomorrow)
        assertEquals(setOf(PlannedDraft(tomorrow, Slot.MORNING)),
            DraftStore(context).use { it.recent().map { d -> PlannedDraft(d.day, d.slot) }.toSet() })
        DraftWorker.runOnce(context, sample = false, manual = true, targetDay = day)
        assertEquals(4, generated)
        val drafts = DraftStore(context).use { it.recent() }
        assertEquals(4, drafts.size)
        assertEquals(true, drafts.all { it.timing?.origin == DraftOrigin.MANUAL })
        DraftWorker.runOnce(context, sample = false, manual = true, targetDay = day)
        assertEquals(4, generated)
    }

    @Test fun editedSlotControlsGenerationAndSavedTargetSurvivesLaterEdits() {
        val settings = context.getSharedPreferences("bam", Context.MODE_PRIVATE)
        val target = LocalTime.of(11, 0)
        PostingSchedule.save(settings, Slot.MORNING, PostingRule(target, setOf(DayOfWeek.SATURDAY)))
        now = Instant.parse("2026-11-14T15:30:00Z")
        setEnabled(true)
        DraftWorker.runOnce(context, sample = false)
        assertEquals(0, generated)

        now = Instant.parse("2026-11-14T16:03:00Z")
        DraftWorker.runOnce(context, sample = false)
        assertEquals(1, generated)
        DraftStore(context).use { store ->
            val draft = checkNotNull(store.find(day, Slot.MORNING))
            assertEquals(target, draft.postingTime)
            assertEquals("3 min after posting time",
                draft.timing?.description(day, Slot.MORNING)?.substringAfterLast(" · "))
            assertEquals(true, store.setApproval(draft, true))
        }

        PostingSchedule.save(settings, Slot.MORNING, PostingRule(LocalTime.of(9, 30), emptySet()))
        val schedule = PostingSchedule.read(settings)
        assertEquals(false, Slot.MORNING in Schedule.planned(day, day, schedule))
        assertEquals(false, Slot.MORNING in Schedule.planned(day.plusDays(1), day.plusDays(1), schedule))
        DraftStore(context).use { store ->
            val draft = checkNotNull(store.find(day, Slot.MORNING))
            assertEquals(target, draft.postingTime)
            assertEquals(true, draft.review.approved)
        }
    }

    private fun setEnabled(enabled: Boolean) {
        context.getSharedPreferences("bam", Context.MODE_PRIVATE).edit()
            .putBoolean("enabled", enabled).commit()
    }

    private fun workInfo(name: String) =
        manager.getWorkInfosForUniqueWork(name).get(5, TimeUnit.SECONDS).single()
}
