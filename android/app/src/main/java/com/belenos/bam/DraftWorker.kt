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

class DraftWorker(private val context: Context, parameters: WorkerParameters) :
    Worker(context, parameters) {
    override fun doWork(): Result = synchronized(generationLock) {
        if (isStopped) return@synchronized Result.success()
        val model = ModelFile(context)
        val settings = context.getSharedPreferences("bam", Context.MODE_PRIVATE)
        val sample = inputData.getBoolean("sample", false)
        val manual = inputData.getBoolean("manual", false)
        val allowed = { sample || manual || settings.getBoolean("enabled", false) }
        if (!model.ready() || !allowed()) {
            return@synchronized Result.success()
        }
        val now = Instant.now()
        val day = now.atZone(Schedule.eastern).toLocalDate()
        val confirmedThrough = LocalDate.parse(settings.getString("hours_through", "2026-12-10"))
        DraftStore(context).use { store ->
            val campaign = store.campaign(day)
            val slots = if (sample) listOf(Slot.SAMPLE) else Schedule.due(now, confirmedThrough, campaign)
                .filterNot { store.contains(day, it) }
            if (slots.isEmpty()) {
                if (manual) settings.edit().putString("status", "No missing drafts are due today.").apply()
                return@synchronized Result.success()
            }
            settings.edit().putString("status", "Writing on-device…").apply()
            var failed = false
            var planChanged = false
            try {
                Engine(EngineConfig(modelPath = checkNotNull(model.file).absolutePath,
                    backend = Backend.CPU(), maxNumTokens = 2048, cacheDir = context.cacheDir.path)).use { engine ->
                    engine.initialize()
                    for (slot in slots) {
                        if (isStopped || !allowed()) break
                        if (slot == Slot.OPENING && Slot.OPENING !in Schedule.due(
                                Instant.now(), confirmedThrough, campaign)) continue
                        try {
                            val recent = store.recent(4).filter { it.slot != Slot.SAMPLE }.map { it.caption }
                            val text = engine.createConversation(ConversationConfig(
                                samplerConfig = SamplerConfig(topK = 25, topP = 0.9, temperature = 0.75),
                                maxOutputToken = 220
                            )).use { chat ->
                                chat.sendMessage(Schedule.prompt(day, slot, recent, campaign))
                                    .contents.contents.filterIsInstance<Content.Text>()
                                    .joinToString("") { it.text }
                            }
                            val hours = if (slot == Slot.OPENING) Schedule.hours(day, confirmedThrough) else null
                            val caption = Schedule.caption(text, hours)
                            val finished = Instant.now()
                            val currentHours = LocalDate.parse(settings.getString("hours_through", "2026-12-10"))
                            if (!isStopped && allowed() &&
                                day == finished.atZone(Schedule.eastern).toLocalDate() &&
                                (sample || slot in Schedule.due(finished, currentHours, campaign))) {
                                if (!store.saveGenerated(Draft(day, slot, caption), campaign)) {
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

        fun enable(context: Context) {
            WorkManager.getInstance(context).enqueueUniquePeriodicWork("scheduled-drafts",
                ExistingPeriodicWorkPolicy.KEEP,
                PeriodicWorkRequestBuilder<DraftWorker>(15, TimeUnit.MINUTES).build())
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
                    .setInputData(workDataOf("sample" to sample, "manual" to manual)).build())
        }
    }
}
