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
        if (!model.ready() || (!sample && !settings.getBoolean("enabled", false))) {
            return@synchronized Result.success()
        }
        val now = Instant.now()
        val day = now.atZone(Schedule.eastern).toLocalDate()
        val confirmedThrough = LocalDate.parse(settings.getString("hours_through", "2026-12-10"))
        DraftStore(context).use { store ->
            val slots = if (sample) listOf(Slot.SAMPLE) else Schedule.due(now, confirmedThrough)
                .filterNot { store.contains(day, it) }
            if (slots.isEmpty()) return@synchronized Result.success()
            settings.edit().putString("status", "Writing on-device…").apply()
            var failed = false
            try {
                Engine(EngineConfig(modelPath = checkNotNull(model.file).absolutePath,
                    backend = Backend.CPU(), maxNumTokens = 2048, cacheDir = context.cacheDir.path)).use { engine ->
                    engine.initialize()
                    for (slot in slots) {
                        if (isStopped || (!sample && !settings.getBoolean("enabled", false))) break
                        if (slot == Slot.OPENING && Slot.OPENING !in Schedule.due(
                                Instant.now(), confirmedThrough)) continue
                        try {
                            val recent = store.recent(4).filter { it.slot != Slot.SAMPLE }.map { it.caption }
                            val text = engine.createConversation(ConversationConfig(
                                samplerConfig = SamplerConfig(topK = 25, topP = 0.9, temperature = 0.75),
                                maxOutputToken = 220
                            )).use { chat ->
                                chat.sendMessage(Schedule.prompt(day, slot, recent))
                                    .contents.contents.filterIsInstance<Content.Text>()
                                    .joinToString("") { it.text }
                            }
                            val hours = if (slot == Slot.OPENING) Schedule.hours(day, confirmedThrough) else null
                            val caption = Schedule.caption(text, hours)
                            if (!isStopped && (sample || settings.getBoolean("enabled", false)) &&
                                day == Instant.now().atZone(Schedule.eastern).toLocalDate() &&
                                (slot != Slot.OPENING || Slot.OPENING in Schedule.due(
                                    Instant.now(), confirmedThrough))) {
                                store.save(Draft(day, slot, caption), replace = sample)
                            }
                        } catch (_: Exception) {
                            failed = true
                        }
                    }
                    settings.edit().putString("status", if (failed)
                        "One or more drafts failed validation. BAM will retry scheduled drafts."
                        else "Draft inbox is up to date.").apply()
                }
            } catch (_: Exception) {
                failed = true
                settings.edit().putString("status", "The local model could not start. Check storage and retry.").apply()
            } catch (_: LinkageError) {
                failed = true
                settings.edit().putString("status", "The AI runtime could not load on this phone.").apply()
            }
            if (failed && !sample) Result.retry() else Result.success()
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

        fun runOnce(context: Context, sample: Boolean) {
            WorkManager.getInstance(context).enqueueUniqueWork(
                if (sample) "sample-draft" else "catch-up", ExistingWorkPolicy.KEEP,
                OneTimeWorkRequestBuilder<DraftWorker>()
                    .setInputData(workDataOf("sample" to sample)).build())
        }
    }
}
