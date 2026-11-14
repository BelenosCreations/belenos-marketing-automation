package com.belenos.bam

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputFilter
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import java.time.LocalDate
import java.time.Instant
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private val modelExecutor = Executors.newSingleThreadExecutor()
    private val preferences by lazy { getSharedPreferences("bam", Context.MODE_PRIVATE) }
    private val model by lazy { ModelFile(applicationContext) }
    private val muted by lazy { getColor(R.color.bam_muted) }
    private lateinit var status: TextView
    private lateinit var download: Button
    private lateinit var sample: Button
    private lateinit var catchUp: Button
    private lateinit var automatic: Switch
    private lateinit var timingReport: TextView
    private lateinit var inbox: LinearLayout
    private var displayed: List<Draft>? = null
    private var checkingModel = false
    private var downloadMessage: String? = null

    private val refresh = object : Runnable {
        override fun run() {
            if (!checkingModel && model.downloading()) {
                checkingModel = true
                modelExecutor.execute {
                    val result = runCatching { model.checkDownload() }
                        .getOrElse { "Could not check the model download. Open BAM again to retry." }
                    runOnUiThread {
                        checkingModel = false
                        downloadMessage = result
                        if (!isFinishing && !isDestroyed) redraw()
                    }
                }
            }
            redraw()
            handler.postDelayed(this, 2500)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(getColor(R.color.bam_navy))
            setOnApplyWindowInsetsListener { view, insets ->
                if (android.os.Build.VERSION.SDK_INT >= 30) {
                    val bars = insets.getInsets(WindowInsets.Type.systemBars())
                    view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                } else {
                    @Suppress("DEPRECATION")
                    view.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop,
                        insets.systemWindowInsetRight, insets.systemWindowInsetBottom)
                }
                insets
            }
        }
        val header = column().apply {
            setPadding(dp(22), dp(14), dp(22), dp(13))
            addView(ImageView(this@MainActivity).apply {
                setImageResource(R.drawable.bam_wordmark_dark)
                scaleType = ImageView.ScaleType.FIT_START
                contentDescription = "BAM — Belenos Automatic Marketing"
            }, LinearLayout.LayoutParams(-1, dp(56)))
            addView(text("Belenos Creations · Facebook", 15, getColor(R.color.bam_silver)).apply {
                setPadding(0, dp(7), 0, 0)
            })
        }
        root.addView(header)
        root.addView(View(this).apply { setBackgroundColor(getColor(R.color.bam_gold)) },
            LinearLayout.LayoutParams(-1, dp(2)))
        val content = column().apply { setPadding(dp(16), dp(14), dp(16), dp(22)) }
        root.addView(ScrollView(this).apply {
            setBackgroundColor(getColor(R.color.bam_page))
            addView(content)
        }, LinearLayout.LayoutParams(-1, 0, 1f))
        val controls = card(content)
        controls.addView(text("Draft schedule", 20, bold = true))
        controls.addView(text("10 AM daily · Morning\n10 AM Thu–Sat · Draft the 11:30 AM opening reminder\n6:30 PM Mon, Wed, Fri, Sat · Evening", 15))
        controls.addView(text("Eastern time. Android may delay background drafts. Opening reminders require confirmed hours.", 13, muted))
        automatic = Switch(this).apply {
            text = "Generate scheduled drafts"
            isChecked = preferences.getBoolean("enabled", false)
            setOnCheckedChangeListener { _, enabled ->
                preferences.edit().putBoolean("enabled", enabled).apply()
                if (enabled) {
                    DraftWorker.enable(applicationContext)
                    DraftWorker.runOnce(applicationContext, sample = false)
                } else DraftWorker.disable(applicationContext)
                redraw()
            }
        }
        controls.addView(automatic)
        controls.addView(button("Confirm regular store hours") { confirmHours() })
        controls.addView(button("Campaign notes and skips") { chooseCampaignDay() })
        download = button("Download offline AI · 1.6 GB") {
            try {
                model.start()
                downloadMessage = "Model download started. Connect to Wi-Fi to continue."
            } catch (error: Exception) {
                downloadMessage = error.message ?: "Could not start the model download."
            }
            redraw()
        }
        controls.addView(download)
        sample = button("Generate test draft") {
            preferences.edit().putString("status", "Test draft queued…").apply()
            DraftWorker.runOnce(applicationContext, sample = true)
            redraw()
        }
        controls.addView(sample)
        catchUp = button("Generate due drafts now") {
            preferences.edit().putString("status", "Checking for missing drafts…").apply()
            DraftWorker.runOnce(applicationContext, sample = false, manual = true)
            redraw()
        }
        controls.addView(catchUp)
        status = text("", 14, muted).apply { accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE }
        controls.addView(status)
        val timing = card(content)
        timing.addView(text("Today's draft timing", 20, bold = true))
        timingReport = text("", 14, muted).apply { setTextIsSelectable(true) }
        timing.addView(timingReport)
        content.addView(text("Draft inbox", 21, bold = true).apply {
            setPadding(dp(2), dp(6), 0, dp(9))
        })
        inbox = column()
        content.addView(inbox)
        setContentView(root)
        root.requestApplyInsets()
    }

    override fun onStart() {
        super.onStart()
        if (preferences.getBoolean("enabled", false)) {
            DraftWorker.enable(applicationContext)
            DraftWorker.runOnce(applicationContext, sample = false)
        }
        handler.post(refresh)
    }

    override fun onStop() {
        handler.removeCallbacks(refresh)
        super.onStop()
    }

    override fun onDestroy() {
        modelExecutor.shutdown()
        super.onDestroy()
    }

    private fun confirmHours() {
        val input = EditText(this).apply {
            hint = "YYYY-MM-DD"
            setSingleLine()
            setText(preferences.getString("hours_through", "2026-12-10"))
        }
        val dialog = android.app.AlertDialog.Builder(this).setTitle("Regular hours confirmed through")
            .setMessage("Thursday and Friday noon–3 PM and 4–7 PM, Saturday noon–7 PM. The known holiday closure still applies.")
            .setView(input).setNegativeButton("Cancel", null).setPositiveButton("Save", null).create()
        dialog.setOnShowListener {
            dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val day = runCatching { LocalDate.parse(input.text.toString().trim()) }.getOrNull()
                if (day == null) {
                    input.error = "Enter a date as YYYY-MM-DD."
                    return@setOnClickListener
                }
                preferences.edit().putString("hours_through", day.toString()).apply()
                if (automatic.isChecked) DraftWorker.runOnce(applicationContext, sample = false)
                dialog.dismiss()
                redraw()
            }
        }
        dialog.show()
    }

    private fun redraw() {
        val ready = model.ready()
        val pending = model.downloading()
        download.visibility = if (ready) View.GONE else View.VISIBLE
        download.isEnabled = !pending && !checkingModel
        sample.visibility = if (ready) View.VISIBLE else View.GONE
        catchUp.visibility = if (ready) View.VISIBLE else View.GONE
        automatic.isEnabled = ready || automatic.isChecked
        val currentStatus = when {
            checkingModel -> "Checking the offline model…"
            pending || !ready -> downloadMessage ?: "Download the model once to enable offline drafting."
            else -> preferences.getString("status", null) ?: "Model ready. Enable scheduled drafts or run a test."
        }
        if (status.text.toString() != currentStatus) status.text = currentStatus
        val now = Instant.now()
        val day = now.atZone(Schedule.eastern).toLocalDate()
        val (drafts, campaign) = DraftStore(this).use { it.recent() to it.campaign(day) }
        val confirmedThrough = LocalDate.parse(preferences.getString("hours_through", "2026-12-10"))
        val todaysDrafts = drafts.filter { it.day == day }.associateBy(Draft::slot)
        val planned = Schedule.planned(day, confirmedThrough)
        val timingRows = listOf(Slot.MORNING, Slot.OPENING, Slot.EVENING).filter { slot ->
            slot in planned || slot in todaysDrafts
        }.map { slot ->
            val target = checkNotNull(slot.draftTime).format(timingClock)
            val detail = slotStatus(day, slot, now, slot in campaign.skipped, todaysDrafts[slot])
            "${slot.title.substringBefore(" ·")} · target $target ET\n$detail"
        }
        val report = buildString {
            if (!automatic.isChecked) append("Automatic drafting is paused.\n\n")
            append(timingRows.joinToString("\n\n").ifEmpty { "No drafts scheduled for today." })
        }
        if (timingReport.text.toString() != report) timingReport.text = report
        if (drafts == displayed) return
        displayed = drafts
        inbox.removeAllViews()
        if (drafts.isEmpty()) {
            inbox.addView(text("Your drafts will appear here after generation.", 15, muted))
        }
        for (draft in drafts) {
            val panel = card(inbox)
            panel.addView(text(draft.slot.title, 17, bold = true))
            panel.addView(text(draft.day.format(DateTimeFormatter.ofPattern("EEE, MMM d")), 13, muted))
            draft.timing?.let { panel.addView(text(it.description(draft.day, draft.slot), 13, muted)) }
            panel.addView(text(draft.caption, 16).apply {
                setPadding(0, dp(10), 0, dp(9))
                setTextIsSelectable(true)
            })
            panel.addView(button("Edit caption") { editCaption(draft) })
            panel.addView(button("Copy caption") {
                getSystemService(ClipboardManager::class.java).setPrimaryClip(
                    ClipData.newPlainText("BAM caption", draft.caption))
                Toast.makeText(this, "Caption copied", Toast.LENGTH_SHORT).show()
            })
        }
    }

    private fun chooseCampaignDay() {
        val today = Instant.now().atZone(Schedule.eastern).toLocalDate()
        val picker = android.app.DatePickerDialog(this, { _, year, month, day ->
            editCampaign(LocalDate.of(year, month + 1, day))
        }, today.year, today.monthValue - 1, today.dayOfMonth)
        picker.show()
    }

    private fun editCampaign(day: LocalDate) {
        val campaign = DraftStore(this).use { it.campaign(day) }
        val controls = column().apply { setPadding(dp(22), 0, dp(22), 0) }
        val focus = input("Campaign topic", campaign.focus, 160)
        val facts = input("Confirmed facts for this date", campaign.facts, 500)
        controls.addView(focus)
        controls.addView(facts)
        val skipControls = listOf(Slot.MORNING, Slot.OPENING, Slot.EVENING).associateWith { slot ->
            CheckBox(this).apply {
                text = "Skip ${slot.title.substringBefore(" ·").lowercase()}"
                isChecked = slot in campaign.skipped
                controls.addView(this)
            }
        }
        controls.addView(text("Applies to drafts still to be generated.", 13, muted))
        AlertDialog.Builder(this).setTitle(day.format(DateTimeFormatter.ofPattern("EEE, MMM d, uuuu")))
            .setView(ScrollView(this).apply { addView(controls) })
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Save") { _, _ ->
                val updated = Campaign(focus.text.toString().trim(), facts.text.toString().trim(),
                    skipControls.filterValues { it.isChecked }.keys)
                DraftStore(this).use { it.saveCampaign(day, updated) }
                Toast.makeText(this, "Campaign saved", Toast.LENGTH_SHORT).show()
                if (automatic.isChecked) DraftWorker.runOnce(applicationContext, sample = false)
            }.show()
    }

    private fun editCaption(draft: Draft) {
        val editor = input("Facebook caption", draft.caption, 4000).apply { minLines = 4 }
        val dialog = AlertDialog.Builder(this).setTitle("Edit caption").setView(editor)
            .setNegativeButton("Cancel", null).setPositiveButton("Save", null).create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val caption = editor.text.toString().trim()
                if (caption.isEmpty()) {
                    editor.error = "Enter a caption."
                    return@setOnClickListener
                }
                val saved = DraftStore(this).use { it.edit(draft, caption) }
                if (!saved) {
                    editor.error = "This draft changed. Reopen the editor before saving."
                    return@setOnClickListener
                }
                dialog.dismiss()
                redraw()
            }
        }
        dialog.show()
    }

    private fun input(label: String, value: String, maxLength: Int) = EditText(this).apply {
        hint = label
        filters = arrayOf(InputFilter.LengthFilter(maxLength))
        setText(value)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density + .5f).toInt()

    private fun column() = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }

    private fun text(label: String, size: Int, color: Int = getColor(R.color.bam_text), bold: Boolean = false) =
        TextView(this).apply {
            text = label
            textSize = size.toFloat()
            setTextColor(color)
            if (bold) setTypeface(typeface, Typeface.BOLD)
            setLineSpacing(dp(2).toFloat(), 1f)
        }

    private fun button(label: String, action: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        setOnClickListener { action() }
    }

    private fun card(parent: LinearLayout): LinearLayout = column().apply {
        background = GradientDrawable().apply {
            setColor(getColor(R.color.bam_surface))
            setStroke(dp(1), getColor(R.color.bam_border))
            cornerRadius = dp(14).toFloat()
        }
        setPadding(dp(16), dp(14), dp(16), dp(14))
        parent.addView(this, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
    }

    companion object {
        private val timingClock = DateTimeFormatter.ofPattern("h:mm a", Locale.US)
    }
}
