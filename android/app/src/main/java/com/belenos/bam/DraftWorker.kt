package com.belenos.bam

import android.content.Context
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.google.ai.edge.litertlm.Backend
import com.google.ai.edge.litertlm.Content
import com.google.ai.edge.litertlm.ConversationConfig
import com.google.ai.edge.litertlm.Engine
import com.google.ai.edge.litertlm.EngineConfig
import com.google.ai.edge.litertlm.SamplerConfig
import java.time.Instant
import java.time.LocalDate
import java.util.concurrent.TimeUnit

class DraftWorker internal constructor(
    private val context: Context,
    parameters: WorkerParameters,
    private val now: () -> Instant,
    private val modelReady: () -> Boolean,
    private val withGenerator: ((String) -> String) -> Unit
) : Worker(context, parameters) {
    constructor(context: Context, parameters: WorkerParameters) : this(
        context, parameters, Instant::now, { ModelFile(context).ready() },
        { useGenerator(context, it) }
    )

    override fun doWork(): Result = synchronized(generationLock) {
        if (isStopped) return@synchronized Result.success()
        val settings = context.getSharedPreferences("bam", Context.MODE_PRIVATE)
        val sample = inputData.getBoolean("sample", false)
        val manual = inputData.getBoolean("manual", false)
        val origin = when {
            sample -> DraftOrigin.TEST
            manual -> DraftOrigin.MANUAL
            inputData.getBoolean("app_catch_up", false) -> DraftOrigin.APP_OPEN
            inputData.getBoolean("periodic", false) -> DraftOrigin.BACKGROUND
            else -> DraftOrigin.UNKNOWN
        }
        val allowed = { sample || manual || settings.getBoolean("enabled", false) }
        if (!allowed()) return@synchronized Result.success()
        if (!modelReady()) {
            if (sample || manual) settings.edit().putString("status", "The offline model is unavailable.").apply()
            return@synchronized Result.success()
        }
        fun confirmedThrough() = LocalDate.parse(settings.getString("hours_through", "2026-12-10"))
        val started = now()
        val day = started.atZone(Schedule.eastern).toLocalDate()
        DraftStore(context).use { store ->
            val campaign = store.campaign(day)
            val slots = if (sample) listOf(Slot.SAMPLE) else Schedule.due(started, confirmedThrough(), campaign)
                .filterNot { store.contains(day, it) }
            if (slots.isEmpty()) {
                if (manual) settings.edit().putString("status", "No missing drafts are due today.").apply()
                return@synchronized Result.success()
            }
            settings.edit().putString("status", "Writing on-device…").apply()
            var failed = false
            var planChanged = false
            try {
                withGenerator { generate ->
                    for (slot in slots) {
                        if (isStopped || !allowed()) break
                        val before = now()
                        if (day != before.atZone(Schedule.eastern).toLocalDate()) break
                        if (!sample && slot !in Schedule.due(before, confirmedThrough(), campaign)) continue
                        try {
                            val recent = store.recent(4).filter { it.slot != Slot.SAMPLE }.map { it.caption }
                            val text = generate(Schedule.prompt(day, slot, recent, campaign))
                            val finished = now()
                            val currentHours = confirmedThrough()
                            if (!isStopped && allowed() &&
                                day == finished.atZone(Schedule.eastern).toLocalDate() &&
                                (sample || slot in Schedule.due(finished, currentHours, campaign))) {
                                val hours = if (slot == Slot.OPENING) Schedule.hours(day, currentHours) else null
                                val caption = Schedule.caption(text, hours)
                                val draft = Draft(day, slot, caption, DraftTiming(finished, origin))
                                if (!store.saveGenerated(draft, campaign)) {
                                    planChanged = true
                                    break
                                }
                            }
                        } catch (_: Exception) {
                            failed = true
                        }
                    }
                    val status = when {
                        planChanged -> "Campaign changed during drafting. Generate due drafts again."
                        !failed -> "Draft inbox is up to date."
                        sample || manual -> "A draft could not be generated. Try again."
                        else -> "A scheduled draft failed. BAM will retry."
                    }
                    settings.edit().putString("status", status).apply()
                }
            } catch (_: Exception) {
                failed = true
                settings.edit().putString("status", "The local model could not start. Check storage and retry.").apply()
            } catch (_: LinkageError) {
                failed = true
                settings.edit().putString("status", "The AI runtime could not load on this phone.").apply()
            }
            if ((failed || planChanged) && !sample && !manual) Result.retry() else Result.success()
        }
    }

    companion object {
        private val generationLock = Any()

        private fun useGenerator(context: Context, consume: ((String) -> String) -> Unit) {
            val model = checkNotNull(ModelFile(context).file)
            Engine(EngineConfig(modelPath = model.absolutePath,
                backend = Backend.CPU(), maxNumTokens = 2048, cacheDir = context.cacheDir.path)).use { engine ->
                engine.initialize()
                consume { prompt ->
                    engine.createConversation(ConversationConfig(
                        samplerConfig = SamplerConfig(topK = 25, topP = 0.9, temperature = 0.75),
                        maxOutputToken = 220
                    )).use { chat ->
                        chat.sendMessage(prompt).contents.contents.filterIsInstance<Content.Text>()
                            .joinToString("") { it.text }
                    }
                }
            }
        }

        fun enable(context: Context) {
            WorkManager.getInstance(context).enqueueUniquePeriodicWork("scheduled-drafts",
                ExistingPeriodicWorkPolicy.UPDATE,
                PeriodicWorkRequestBuilder<DraftWorker>(15, TimeUnit.MINUTES)
                    .setInputData(workDataOf("periodic" to true)).build())
        }

        fun disable(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork("scheduled-drafts")
            WorkManager.getInstance(context).cancelUniqueWork("catch-up")
        }

        fun runOnce(context: Context, sample: Boolean, manual: Boolean = false) {
            WorkManager.getInstance(context).enqueueUniqueWork(
                when { sample -> "sample-draft"; manual -> "manual-drafts"; else -> "catch-up" },
                ExistingWorkPolicy.KEEP,
                OneTimeWorkRequestBuilder<DraftWorker>()
                    .setInputData(workDataOf("sample" to sample, "manual" to manual,
                        "app_catch_up" to (!sample && !manual))).build())
        }
    }
}
