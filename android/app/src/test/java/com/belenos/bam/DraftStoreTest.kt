package com.belenos.bam

import android.app.Application
import android.content.Context
import androidx.work.Data
import androidx.work.ListenableWorker.Result
import androidx.work.WorkerParameters
import androidx.work.ListenableWorker
import androidx.work.WorkerFactory
import androidx.work.testing.TestWorkerBuilder
import java.time.Instant
import java.time.LocalDate
import java.util.concurrent.Executor
import org.junit.Before
import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class DraftStoreTest {
    private val day = LocalDate.parse("2026-11-14")
    private val timing = DraftTiming(Instant.parse("2026-11-14T15:08:00Z"), DraftOrigin.BACKGROUND)
    private lateinit var context: Application

    @Before fun setUp() {
        context = RuntimeEnvironment.getApplication()
        context.deleteDatabase("drafts.db")
    }

    @Test fun schemaOneUpgradePreservesCaptionAndCreatesCampaigns() {
        seedLegacyStore(version = 1)
        DraftStore(context).use { store ->
            assertEquals(listOf(Draft(day, Slot.MORNING, "My edited caption")), store.recent())
            assertEquals(Campaign(), store.campaign(day))
            store.saveCampaign(day, Campaign("Tumblers"))
            assertEquals(Campaign("Tumblers"), store.campaign(day))
        }
    }

    @Test fun schemaTwoUpgradePreservesCampaignsAndRecordsNewDraftTiming() {
        seedLegacyStore(version = 2)
        val campaign = Campaign("Tumblers", "20 oz", setOf(Slot.EVENING))
        val draft = Draft(day, Slot.OPENING, "Visit us today", timing)
        DraftStore(context).use { store ->
            assertEquals(campaign, store.campaign(day))
            val original = store.recent().single()
            assertEquals(Draft(day, Slot.MORNING, "My edited caption"), original)
            assertTrue(store.edit(original, "Updated caption"))
            assertTrue(store.saveGenerated(draft, campaign))
        }
        DraftStore(context).use { store ->
            val stored = store.recent().associateBy(Draft::slot)
            assertEquals(draft, stored[Slot.OPENING])
            assertEquals(Draft(day, Slot.MORNING, "Updated caption"), stored[Slot.MORNING])
        }
    }

    @Test fun revisedCampaignAndRepeatedWorkPreserveExistingCaption() {
        val original = Draft(day, Slot.MORNING, "First draft", timing)
        val initialPlan = Campaign("Tumblers")
        val revisedPlan = Campaign("Pet memorials", skipped = setOf(Slot.OPENING))
        DraftStore(context).use { inbox ->
            inbox.saveCampaign(day, initialPlan)
            assertTrue(inbox.saveGenerated(original, initialPlan))
            assertTrue(inbox.edit(original, "Owner's caption"))
            assertFalse(inbox.edit(original, "Edit from an older screen"))
            inbox.saveCampaign(day, revisedPlan)
        }
        DraftStore(context).use { worker ->
            assertFalse(worker.saveGenerated(original.copy(slot = Slot.OPENING), initialPlan))
            assertTrue(worker.saveGenerated(original.copy(caption = "Retry output"), revisedPlan))
            assertFalse(worker.contains(day, Slot.OPENING))
            assertEquals(listOf(original.copy(caption = "Owner's caption")), worker.recent())
        }
    }

    @Test fun workerLeavesOpeningSlotEmptyWhenGenerationCrossesNoon() {
        var at = Instant.parse("2026-11-14T16:59:55Z")
        val result = runWorker(now = { at }) { prompt ->
            if (prompt.contains("reason to stop in")) at = Instant.parse("2026-11-14T17:00:01Z")
            "Ask us about custom gifts."
        }
        assertEquals(Result.success(), result)
        val saved = DraftStore(context).use { it.recent().single() }
        assertEquals(Slot.MORNING, saved.slot)
        assertEquals(DraftOrigin.BACKGROUND, saved.timing?.origin)
    }

    @Test fun workerDoesNotSaveYesterdayAfterMidnight() {
        var at = Instant.parse("2026-11-15T04:59:55Z")
        val result = runWorker(now = { at }) {
            at = Instant.parse("2026-11-15T05:00:01Z")
            "Ask us about custom gifts."
        }
        assertEquals(Result.success(), result)
        assertTrue(DraftStore(context).use { it.recent().isEmpty() })
    }

    @Test fun workerRetriesWhenTheCampaignChangesDuringGeneration() {
        val result = runWorker {
            DraftStore(context).use { store ->
                store.saveCampaign(day, Campaign("Skip morning", skipped = setOf(Slot.MORNING)))
            }
            "Ask us about custom gifts."
        }
        assertEquals(Result.retry(), result)
        assertTrue(DraftStore(context).use { it.recent().isEmpty() })
    }

    @Test fun workerWithholdsAnOpeningDraftWhenHoursAreWithdrawn() {
        val result = runWorker { prompt ->
            if (prompt.contains("reason to stop in")) {
                context.getSharedPreferences("bam", Context.MODE_PRIVATE).edit()
                    .putString("hours_through", "2026-11-13").commit()
            }
            "Ask us about custom gifts."
        }
        assertEquals(Result.success(), result)
        assertEquals(Slot.MORNING, DraftStore(context).use { it.recent().single().slot })
    }

    private fun runWorker(
        now: () -> Instant = { timing.savedAt },
        generate: (String) -> String
    ): Result {
        context.getSharedPreferences("bam", Context.MODE_PRIVATE).edit().putBoolean("enabled", true).commit()
        val executor = Executor { it.run() }
        val factory = object : WorkerFactory() {
            override fun createWorker(appContext: Context, workerClassName: String,
                workerParameters: WorkerParameters): ListenableWorker =
                DraftWorker(appContext, workerParameters, now, { true }, { it(generate) })
        }
        return TestWorkerBuilder<DraftWorker>(context, executor)
            .setInputData(Data.Builder().putBoolean("periodic", true).build())
            .setWorkerFactory(factory).build().doWork()
    }

    private fun seedLegacyStore(version: Int) {
        context.openOrCreateDatabase("drafts.db", Context.MODE_PRIVATE, null).use { db ->
            db.execSQL("""CREATE TABLE draft (
                day TEXT NOT NULL, slot TEXT NOT NULL, caption TEXT NOT NULL,
                PRIMARY KEY (day, slot)
            )""")
            db.execSQL("INSERT INTO draft VALUES (?, ?, ?)",
                arrayOf(day.toString(), Slot.MORNING.name, "My edited caption"))
            if (version == 2) {
                db.execSQL("""CREATE TABLE campaign (
                    day TEXT PRIMARY KEY NOT NULL, focus TEXT NOT NULL,
                    facts TEXT NOT NULL, skipped TEXT NOT NULL
                )""")
                db.execSQL("INSERT INTO campaign VALUES (?, ?, ?, ?)",
                    arrayOf(day.toString(), "Tumblers", "20 oz", Slot.EVENING.name))
            }
            db.version = version
        }
    }
}
