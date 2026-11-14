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
import java.time.Instant
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
        val draft = DraftStore(context).use { it.recent().single() }
        assertEquals(Slot.MORNING, draft.slot)
        assertEquals(DraftTiming(now, DraftOrigin.MANUAL), draft.timing)
    }

    private fun setEnabled(enabled: Boolean) {
        context.getSharedPreferences("bam", Context.MODE_PRIVATE).edit()
            .putBoolean("enabled", enabled).commit()
    }

    private fun workInfo(name: String) =
        manager.getWorkInfosForUniqueWork(name).get(5, TimeUnit.SECONDS).single()
}
