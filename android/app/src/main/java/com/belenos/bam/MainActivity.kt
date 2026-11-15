package com.belenos.bam

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.text.InputFilter
import android.view.View
import android.view.WindowInsets
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import android.window.OnBackInvokedCallback
import android.window.OnBackInvokedDispatcher
import java.time.LocalDate
import java.time.Instant
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private enum class Page(val title: String) {
        HOME("Dashboard"), INBOX("Draft inbox"), SCHEDULE("Schedule"),
        CONTENT("Content needed"), APPROVAL("Needs approval"),
        CAMPAIGN("Campaign notes"), MODEL("Offline AI")
    }

    private val handler = Handler(Looper.getMainLooper())
    private val modelExecutor = Executors.newSingleThreadExecutor()
    private val imageExecutor = Executors.newSingleThreadExecutor()
    private val preferences by lazy { getSharedPreferences("bam", Context.MODE_PRIVATE) }
    private val model by lazy { ModelFile(applicationContext) }
    private val muted by lazy { getColor(R.color.bam_muted) }
    private val backToDashboard by lazy { OnBackInvokedCallback { show(Page.HOME) } }
    private var page = Page.HOME
    private lateinit var scroll: ScrollView
    private lateinit var pageHeader: LinearLayout
    private lateinit var pageTitle: TextView
    private val pages = mutableMapOf<Page, LinearLayout>()
    private val tileDetails = mutableMapOf<Page, TextView>()
    private lateinit var attention: Button
    private lateinit var status: TextView
    private lateinit var scheduleStatus: TextView
    private lateinit var download: Button
    private lateinit var sample: Button
    private lateinit var catchUp: Button
    private lateinit var tomorrow: Button
    private lateinit var leadButton: Button
    private lateinit var automatic: Switch
    private lateinit var timingReport: TextView
    private var displayed: List<Draft>? = null
    private var draftLimit = 30
    private var imageTarget: ImageTarget? = null
    private var checkingModel = false
    private var downloadMessage: String? = null

    private data class ImageTarget(val day: LocalDate, val slot: Slot, val revision: Long)

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
        savedInstanceState?.getBundle("image_target")?.let { saved ->
            imageTarget = ImageTarget(LocalDate.parse(checkNotNull(saved.getString("day"))),
                Slot.valueOf(checkNotNull(saved.getString("slot"))), saved.getLong("revision"))
        }
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
                setImageResource(R.drawable.bam_approved_metallic_primary)
                scaleType = ImageView.ScaleType.FIT_CENTER
                contentDescription = "BAM — Belenos Automatic Marketing"
            }, LinearLayout.LayoutParams(-1, dp(128)))
            addView(text("Belenos Creations · Facebook", 15, getColor(R.color.bam_silver)).apply {
                setPadding(0, dp(7), 0, 0)
            })
        }
        root.addView(header)
        root.addView(View(this).apply { setBackgroundColor(getColor(R.color.bam_gold)) },
            LinearLayout.LayoutParams(-1, dp(2)))
        val content = column().apply { setPadding(dp(16), dp(14), dp(16), dp(22)) }
        scroll = ScrollView(this).apply {
            setBackgroundColor(getColor(R.color.bam_page))
            addView(content)
        }
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        pageTitle = text("", 24, bold = true).apply { isAccessibilityHeading = true }
        pageHeader = column().apply {
            addView(button("Back to dashboard") { show(Page.HOME) })
            addView(pageTitle)
        }
        content.addView(pageHeader)
        for (destination in Page.entries) pages[destination] = column().also { content.addView(it) }
        buildDashboard(pages.getValue(Page.HOME))
        buildSchedule(pages.getValue(Page.SCHEDULE))
        card(pages.getValue(Page.CAMPAIGN)).apply {
            addView(text("Add a topic, confirmed facts, or skips for a date.", 15, muted))
            addView(button("Campaign notes and skips") { chooseCampaignDay() })
        }
        buildModel(pages.getValue(Page.MODEL))
        setContentView(root)
        val restoredPage = Page.entries.firstOrNull { it.name == savedInstanceState?.getString("page") }
        show(restoredPage ?: Page.HOME)
        root.requestApplyInsets()
    }

    private fun buildDashboard(content: LinearLayout) {
        content.addView(text("Dashboard", 25, bold = true).apply {
            isAccessibilityHeading = true
            setPadding(0, 0, 0, dp(12))
        })
        attention = button("") {}.apply {
            minHeight = dp(56)
            isSingleLine = false
        }
        content.addView(attention, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(8) })
        val destinations = listOf(Page.CONTENT, Page.APPROVAL, Page.SCHEDULE, Page.INBOX, Page.CAMPAIGN, Page.MODEL)
        val twoColumns = resources.configuration.screenWidthDp >= 360 && resources.configuration.fontScale <= 1.25f
        for (row in destinations.chunked(if (twoColumns) 2 else 1)) {
            val tiles = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            content.addView(tiles)
            row.forEachIndexed { index, destination ->
                val tile = panel().apply {
                    minimumHeight = dp(112)
                    isFocusable = true
                    foreground = obtainStyledAttributes(intArrayOf(android.R.attr.selectableItemBackground)).let {
                        val ripple = it.getDrawable(0)
                        it.recycle()
                        ripple
                    }
                    setOnClickListener { show(destination) }
                    accessibilityDelegate = object : View.AccessibilityDelegate() {
                        override fun onInitializeAccessibilityNodeInfo(host: View, info: AccessibilityNodeInfo) {
                            super.onInitializeAccessibilityNodeInfo(host, info)
                            info.className = Button::class.java.name
                        }
                    }
                    addView(text(destination.title, 18, bold = true).apply {
                        importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
                    })
                    val detail = text("", 14, muted).apply {
                        importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
                        setPadding(0, dp(5), 0, 0)
                    }
                    tileDetails[destination] = detail
                    addView(detail)
                }
                tiles.addView(tile, LinearLayout.LayoutParams(0, -1, 1f).apply {
                    bottomMargin = dp(10)
                    if (index > 0) marginStart = dp(10)
                })
            }
        }
    }

    private fun buildSchedule(content: LinearLayout) {
        val controls = card(content)
        controls.addView(text("Posting schedule", 20, bold = true))
        controls.addView(text("10 AM daily · Morning post\n11:30 AM Thu–Sat · Opening reminder\n6:30 PM Mon, Wed, Fri, Sat · Evening post", 15))
        controls.addView(text("Eastern time. These are intended posting times; BAM prepares drafts earlier for your review. Posting is always manual.", 13, muted))
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
        leadButton = button("") {
            val selected = Schedule.validLead(preferences.getInt("lead_minutes", Schedule.DEFAULT_LEAD_MINUTES))
            val options = Schedule.leadOptions
            AlertDialog.Builder(this)
                .setTitle("Generate how far ahead of posting?")
                .setSingleChoiceItems(options.map(Schedule::leadLabel).toTypedArray(),
                    options.indexOf(selected)) { dialog, which ->
                    preferences.edit().putInt("lead_minutes", options[which]).apply()
                    dialog.dismiss()
                    if (automatic.isChecked) DraftWorker.runOnce(applicationContext, sample = false)
                    redraw()
                }
                .setNegativeButton("Cancel", null).show()
        }
        controls.addView(leadButton)
        controls.addView(text("Android may delay background generation; choose enough lead time to review drafts.", 13, muted))
        controls.addView(button("Confirm regular store hours") { confirmHours() })
        catchUp = button("Generate today's drafts now") {
            preferences.edit().putString("status", "Preparing today's missing drafts…").apply()
            DraftWorker.runOnce(applicationContext, sample = false, manual = true,
                targetDay = LocalDate.now(Schedule.eastern))
            redraw()
        }
        controls.addView(catchUp)
        tomorrow = button("Generate tomorrow's drafts now") {
            preferences.edit().putString("status", "Preparing tomorrow's missing drafts…").apply()
            DraftWorker.runOnce(applicationContext, sample = false, manual = true,
                targetDay = LocalDate.now(Schedule.eastern).plusDays(1))
            redraw()
        }
        controls.addView(tomorrow)
        controls.addView(text("Generate now works even with automatic drafting off. Existing, edited, approved, and skipped drafts are preserved.", 13, muted))
        scheduleStatus = text("", 14, muted).apply {
            accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        controls.addView(scheduleStatus)
        val timing = card(content)
        timing.addView(text("Today's posting times", 20, bold = true))
        timingReport = text("", 14, muted).apply { setTextIsSelectable(true) }
        timing.addView(timingReport)
    }

    private fun buildModel(content: LinearLayout) {
        val controls = card(content)
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
        status = text("", 14, muted).apply { accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE }
        controls.addView(status)
    }

    private fun show(destination: Page) {
        if (page == Page.INBOX || page == Page.CONTENT || page == Page.APPROVAL) {
            pages.getValue(page).removeAllViews()
        }
        if (Build.VERSION.SDK_INT >= 33 && (page == Page.HOME) != (destination == Page.HOME)) {
            if (destination == Page.HOME) onBackInvokedDispatcher.unregisterOnBackInvokedCallback(backToDashboard)
            else onBackInvokedDispatcher.registerOnBackInvokedCallback(
                OnBackInvokedDispatcher.PRIORITY_DEFAULT, backToDashboard)
        }
        page = destination
        displayed = null
        draftLimit = if (destination == Page.INBOX) 60 else 30
        pageHeader.visibility = if (page == Page.HOME) View.GONE else View.VISIBLE
        pageTitle.text = page.title
        for ((screen, view) in pages) view.visibility = if (screen == page) View.VISIBLE else View.GONE
        scroll.scrollTo(0, 0)
        redraw()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putString("page", page.name)
        imageTarget?.let { target ->
            outState.putBundle("image_target", Bundle().apply {
                putString("day", target.day.toString())
                putString("slot", target.slot.name)
                putLong("revision", target.revision)
            })
        }
    }

    @Suppress("DEPRECATION", "OVERRIDE_DEPRECATION")
    override fun onBackPressed() {
        if (page == Page.HOME) super.onBackPressed() else show(Page.HOME)
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
        imageExecutor.shutdown()
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
        tomorrow.visibility = if (ready) View.VISIBLE else View.GONE
        leadButton.text = "Generate in advance: " + Schedule.leadLabel(
            Schedule.validLead(preferences.getInt("lead_minutes", Schedule.DEFAULT_LEAD_MINUTES)))
        automatic.isEnabled = ready || automatic.isChecked
        val currentStatus = when {
            checkingModel -> "Checking the offline model…"
            pending || !ready -> downloadMessage ?: "Download the model once to enable offline drafting."
            else -> preferences.getString("status", null) ?: "Model ready. Enable scheduled drafts or run a test."
        }
        if (status.text.toString() != currentStatus) status.text = currentStatus
        if (scheduleStatus.text.toString() != currentStatus) scheduleStatus.text = currentStatus
        val now = Instant.now()
        val day = now.atZone(Schedule.eastern).toLocalDate()
        val queue = when (page) {
            Page.CONTENT -> DraftQueue.CONTENT_NEEDED
            Page.APPROVAL -> DraftQueue.NEEDS_APPROVAL
            else -> null
        }
        val (drafts, campaign, counts) = DraftStore(this).use { store ->
            Triple(store.recent(), store.campaign(day), DraftQueue.entries.associateWith(store::count))
        }
        val contentCount = counts.getValue(DraftQueue.CONTENT_NEEDED)
        val approvalCount = counts.getValue(DraftQueue.NEEDS_APPROVAL)
        val confirmedThrough = LocalDate.parse(preferences.getString("hours_through", "2026-12-10"))
        val todaysDrafts = drafts.filter { it.day == day }.associateBy(Draft::slot)
        val planned = Schedule.planned(day, confirmedThrough)
        val draftCount = planned.count { it !in campaign.skipped || it in todaysDrafts }
        val dueCount = DraftStore(this).use { store ->
            Schedule.automaticTargets(now, confirmedThrough,
                preferences.getInt("lead_minutes", Schedule.DEFAULT_LEAD_MINUTES), store::campaign)
                .count { !store.contains(it.day, it.slot) }
        }
        updateTile(Page.SCHEDULE, when (draftCount) {
            0 -> "No slots today"
            1 -> "1 slot today"
            else -> "$draftCount slots today"
        })
        updateTile(Page.INBOX, if (drafts.isEmpty()) "No drafts yet" else "Review, edit or copy")
        updateTile(Page.CONTENT, if (contentCount == 0) "All clear" else draftCountLabel(contentCount))
        updateTile(Page.APPROVAL, if (approvalCount == 0) "All clear" else draftCountLabel(approvalCount))
        updateTile(Page.CAMPAIGN, "Topics, facts and skips")
        updateTile(Page.MODEL, when {
            ready -> "Ready to draft"
            pending || checkingModel -> "Model download in progress"
            else -> "Set up draft generation"
        })
        val alert = when {
            contentCount > 0 -> "${draftCountLabel(contentCount)} with missing content" to Page.CONTENT
            approvalCount > 0 -> "${draftCountLabel(approvalCount)} awaiting approval" to Page.APPROVAL
            pending || checkingModel -> "Offline AI setup in progress" to Page.MODEL
            !ready -> "Set up offline AI to generate drafts" to Page.MODEL
            day > confirmedThrough -> "Confirm store hours for future opening reminders" to Page.SCHEDULE
            dueCount == 1 -> "1 draft ready to generate" to Page.SCHEDULE
            dueCount > 1 -> "$dueCount drafts ready to generate" to Page.SCHEDULE
            else -> null
        }
        attention.visibility = if (alert == null) View.GONE else View.VISIBLE
        if (alert != null && attention.text != alert.first) {
            attention.text = alert.first
            attention.setOnClickListener { show(alert.second) }
        }
        val timingRows = listOf(Slot.MORNING, Slot.OPENING, Slot.EVENING).filter { slot ->
            slot in planned || slot in todaysDrafts
        }.map { slot ->
            val target = checkNotNull(slot.draftTime).format(timingClock)
            val detail = slotStatus(day, slot, now, slot in campaign.skipped, todaysDrafts[slot])
            "${slot.title.substringBefore(" ·")} · post at $target ET\n$detail"
        }
        val report = buildString {
            if (!automatic.isChecked) append("Automatic drafting is paused.\n\n")
            append(timingRows.joinToString("\n\n").ifEmpty { "No drafts scheduled for today." })
        }
        if (timingReport.text.toString() != report) timingReport.text = report
        when {
            queue != null -> renderDrafts(DraftStore(this).use { it.recent(draftLimit + 1, queue) },
                if (page == Page.CONTENT) "No drafts are waiting for content." else "No drafts are waiting for approval.")
            page == Page.INBOX -> renderDrafts(DraftStore(this).use { it.recent(draftLimit + 1) },
                "Your drafts will appear here after generation.")
        }
    }

    private fun draftCountLabel(count: Int) = if (count == 1) "1 draft" else "$count drafts"

    private fun renderDrafts(drafts: List<Draft>, emptyMessage: String) {
        if (drafts == displayed) return
        displayed = drafts
        val content = pages.getValue(page)
        content.removeAllViews()
        if (drafts.isEmpty()) content.addView(text(emptyMessage, 15, muted))
        for (draft in drafts.take(draftLimit)) {
            val panel = card(content)
            val review = draft.review
            panel.addView(text(draft.slot.title, 17, bold = true))
            if (draft.slot == Slot.SAMPLE) {
                panel.addView(text(draft.day.format(DateTimeFormatter.ofPattern("EEE, MMM d")), 13, muted))
            } else {
                Schedule.postingTargetLabel(draft.day, draft.slot)?.let {
                    panel.addView(text(it, 14, getColor(R.color.bam_accent), bold = true))
                }
            }
            draft.timing?.let { panel.addView(text(it.description(draft.day, draft.slot), 13, muted)) }
            panel.addView(text(draft.caption, 16).apply {
                setPadding(0, dp(10), 0, dp(9))
                setTextIsSelectable(true)
            })
            panel.addView(button("Edit caption") { editCaption(draft) })
            panel.addView(button("Image prompt") { editImagePrompt(draft) })
            addImageControls(panel, draft)
            if (draft.slot != Slot.SAMPLE) {
                panel.addView(text(when {
                    review.contentNeeded.isNotEmpty() -> "Content needed · ${review.contentNeeded}"
                    review.approved && review.imageId != null -> "Approved · ready to copy or share image manually"
                    review.approved -> "Approved · ready to copy manually"
                    else -> "Needs approval"
                }, 14, muted))
                panel.addView(button("Content checklist") { editContentNeeded(draft) })
                if (review.contentNeeded.isEmpty()) {
                    panel.addView(button(if (review.approved) "Reopen approval" else "Approve caption") {
                        if (DraftStore(this).use { it.setApproval(draft, !review.approved) }) {
                            if (!review.approved && page == Page.APPROVAL) {
                                Toast.makeText(this, "Approved. Open Draft inbox to copy or share manually.", Toast.LENGTH_SHORT).show()
                            }
                            redraw()
                        } else refreshChangedDraft()
                    })
                }
            }
            if (draft.slot == Slot.SAMPLE || review.approved) panel.addView(button("Copy caption") {
                if (DraftStore(this).use { it.canCopyCaption(draft) }) copyText("BAM caption", draft.caption, "Caption copied")
                else refreshChangedDraft()
            })
            if (draft.slot != Slot.SAMPLE && review.approved && review.imageId != null) {
                panel.addView(button("Share approved image") { shareApprovedImage(draft) })
                panel.addView(text("Choose Facebook or another app to finish posting. Copy the caption separately if needed.", 13, muted))
            }
        }
        if (drafts.size > draftLimit) {
            content.addView(button("Show older drafts") {
                draftLimit += 30
                displayed = null
                redraw()
            })
        }
    }

    private fun addImageControls(panel: LinearLayout, draft: Draft) {
        val id = draft.review.imageId
        if (id != null) {
            val thumbnail = DraftStore(this).use { it.thumbnail(id) }
            val bitmap = thumbnail?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }
            if (bitmap == null) panel.addView(text("Image preview unavailable", 14, muted))
            else panel.addView(ImageView(this).apply {
                setImageBitmap(bitmap)
                scaleType = ImageView.ScaleType.FIT_CENTER
                contentDescription = "Attached draft image"
            }, LinearLayout.LayoutParams(-1, dp(180)))
        }
        panel.addView(button(if (id == null) "Attach image" else "Replace image") { chooseImage(draft) })
        if (id != null) panel.addView(button("Remove image") {
            if (DraftStore(this).use { it.setImage(draft, null) }) redraw() else refreshChangedDraft()
        })
    }

    @Suppress("DEPRECATION")
    private fun chooseImage(draft: Draft) {
        if (imageTarget != null) return
        imageTarget = ImageTarget(draft.day, draft.slot, draft.review.revision)
        if (Build.VERSION.SDK_INT >= 33) {
            try {
                startActivityForResult(Intent(MediaStore.ACTION_PICK_IMAGES).setType("image/*"), PICK_IMAGE)
                return
            } catch (_: ActivityNotFoundException) {
                // Use the system document picker on devices without the photo picker.
            }
        }
        try {
            startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*")
                .addCategory(Intent.CATEGORY_OPENABLE), PICK_IMAGE)
        } catch (_: ActivityNotFoundException) {
            imageTarget = null
            Toast.makeText(this, "No image picker is available.", Toast.LENGTH_SHORT).show()
        }
    }

    @Suppress("DEPRECATION", "OVERRIDE_DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != PICK_IMAGE) return
        val target = imageTarget ?: return
        imageTarget = null
        if (resultCode != RESULT_OK) return
        val uri = data?.data
        if (uri?.scheme != "content") {
            Toast.makeText(this, "Choose an image from the system picker.", Toast.LENGTH_SHORT).show()
            return
        }
        importImage(target, uri)
    }

    private fun importImage(target: ImageTarget, uri: Uri) {
        val app = applicationContext
        imageExecutor.execute {
            val message = try {
                val image = checkNotNull(app.contentResolver.openInputStream(uri)).use { DraftImage.read(it) }
                val saved = DraftStore(app).use { store ->
                    val draft = store.find(target.day, target.slot)
                    draft != null && draft.review.revision == target.revision && store.setImage(draft, image)
                }
                if (saved) "Image saved to draft." else "Draft changed. Choose the image again from the latest draft."
            } catch (error: IllegalArgumentException) {
                error.message ?: "Choose a supported image."
            } catch (_: Exception) {
                "Could not save this image. Choose a readable image and try again."
            }
            runOnUiThread {
                if (!isFinishing && !isDestroyed) {
                    Toast.makeText(this, message, Toast.LENGTH_LONG).show()
                    redraw()
                }
            }
        }
    }

    private fun shareApprovedImage(draft: Draft) {
        // The displayed card may be stale. Check the current persisted approval,
        // caption revision and exact attached image immediately before handoff.
        val allowed = DraftStore(this).use { it.canShareImage(draft) }
        if (!allowed) {
            refreshChangedDraft()
            return
        }
        val send = DraftShareProvider.shareIntent(this, draft) ?: run {
            refreshChangedDraft()
            return
        }
        try {
            val chooser = Intent.createChooser(send, "Share approved draft image")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            startActivity(chooser)
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "No app can receive this image.", Toast.LENGTH_LONG).show()
        }
    }

    private fun refreshChangedDraft() {
        Toast.makeText(this, "Draft changed. Review the latest version.", Toast.LENGTH_SHORT).show()
        redraw()
    }

    private fun copyText(label: String, value: String, message: String) {
        getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText(label, value))
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    private fun editContentNeeded(draft: Draft) {
        val editor = input("Content still needed", draft.review.contentNeeded, 500).apply { minLines = 2 }
        AlertDialog.Builder(this).setTitle("Content checklist")
            .setMessage("List missing photos, details, or other materials. Clear the list when they’re ready.")
            .setView(editor).setNegativeButton("Cancel", null).setPositiveButton("Save") { _, _ ->
                if (DraftStore(this).use { it.setContentNeeded(draft, editor.text.toString()) }) redraw()
                else refreshChangedDraft()
            }.show()
    }

    private fun editImagePrompt(draft: Draft) {
        val starter = "Create a Facebook image for Belenos Creations in Marion, Ohio. " +
            "Use the following caption only as visual context. Keep the main subject clear, with room for cropping. " +
            "Avoid added prices, store hours, logos, and text overlays.\n\nCaption:\n${draft.caption.take(1500)}"
        val editor = input("Image prompt", draft.review.imagePrompt.ifEmpty { starter }, 2400).apply { minLines = 4 }
        val dialog = AlertDialog.Builder(this).setTitle("Image prompt").setView(editor)
            .setMessage("Copy this optional prompt into ChatGPT to make an image.")
            .setNegativeButton("Cancel", null).setPositiveButton("Save prompt") { _, _ ->
                if (DraftStore(this).use { it.setImagePrompt(draft, editor.text.toString()) }) redraw()
                else refreshChangedDraft()
            }.setNeutralButton("Copy prompt", null).create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener {
                val prompt = editor.text.toString().trim()
                if (prompt.isEmpty()) editor.error = "Enter a prompt to copy."
                else copyText("BAM image prompt", prompt, "Image prompt copied")
            }
        }
        dialog.show()
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
                redraw()
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

    private fun updateTile(destination: Page, detail: String) {
        val label = tileDetails.getValue(destination)
        if (label.text != detail) {
            label.text = detail
            (label.parent as View).contentDescription = "${destination.title}. $detail"
        }
    }

    private fun panel(): LinearLayout = column().apply {
        background = GradientDrawable().apply {
            setColor(getColor(R.color.bam_surface))
            setStroke(dp(1), getColor(R.color.bam_border))
            cornerRadius = dp(14).toFloat()
        }
        setPadding(dp(16), dp(14), dp(16), dp(14))
    }

    private fun card(parent: LinearLayout): LinearLayout = panel().also {
        parent.addView(it, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
    }

    companion object {
        private const val PICK_IMAGE = 81
        private val timingClock = DateTimeFormatter.ofPattern("h:mm a", Locale.US)
    }
}
