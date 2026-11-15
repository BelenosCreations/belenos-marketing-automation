package com.belenos.bam

import android.app.Application
import android.app.AlertDialog
import android.content.ClipboardManager
import android.os.Looper
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.TextView
import android.widget.Switch
import java.time.Instant
import java.time.LocalDate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.shadows.ShadowAlertDialog

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class MainActivityTest {
    private lateinit var context: Application

    @Before fun setUp() {
        context = RuntimeEnvironment.getApplication()
        context.deleteDatabase("drafts.db")
    }

    @Test fun inboxShowsTimingAndCopiesTheEditedCaption() {
        val day = LocalDate.parse("2026-11-14")
        val timing = DraftTiming(Instant.parse("2026-11-14T15:08:00Z"), DraftOrigin.BACKGROUND)
        DraftStore(context).use { store ->
            assertTrue(store.saveGenerated(Draft(day, Slot.MORNING, "Original caption", timing), Campaign()))
        }

        Robolectric.buildActivity(MainActivity::class.java).setup().use { controller ->
            shadowOf(Looper.getMainLooper()).idle()
            val activity = controller.get()
            val root = activity.findViewById<View>(android.R.id.content)
            assertEquals(R.mipmap.ic_launcher, activity.applicationInfo.icon)
            assertTrue(root.descendants().filterIsInstance<ImageView>().any {
                it.contentDescription == "BAM — Belenos Automatic Marketing" && it.drawable != null
            })
            root.tile("Draft inbox").performClick()
            assertTrue(root.descendants().filterIsInstance<TextView>().any {
                it.isShown && it.text == "Periodic background check · saved 10:08 AM ET · 8 min after target"
            })

            root.button("Edit caption").performClick()
            shadowOf(Looper.getMainLooper()).idle()
            val dialog = ShadowAlertDialog.getLatestAlertDialog() as AlertDialog
            val editor = dialog.window!!.decorView.descendants().filterIsInstance<EditText>().single()
            editor.setText(" ")
            val save = dialog.getButton(AlertDialog.BUTTON_POSITIVE)
            save.performClick()
            assertEquals("Enter a caption.", editor.error?.toString())
            editor.setText("Edited caption for Facebook")
            save.performClick()

            assertTrue(root.descendants().filterIsInstance<Button>().none { it.text == "Copy caption" })
            root.button("Approve caption").performClick()
            root.button("Copy caption").performClick()
            val clipboard = activity.getSystemService(ClipboardManager::class.java)
            assertEquals("Edited caption for Facebook", clipboard.primaryClip?.getItemAt(0)?.text)
            assertEquals(timing, DraftStore(context).use { it.recent().single().timing })
        }
    }

    @Test fun dashboardRoutesMissingContentAndAllowsAnIndependentImagePrompt() {
        val day = LocalDate.parse("2026-11-14")
        val original = Draft(day, Slot.MORNING, "Ask us about custom prints.",
            DraftTiming(Instant.parse("2026-11-14T15:08:00Z"), DraftOrigin.BACKGROUND))
        DraftStore(context).use { store -> assertTrue(store.saveGenerated(original, Campaign())) }
        Robolectric.buildActivity(MainActivity::class.java).setup().use { controller ->
            shadowOf(Looper.getMainLooper()).idle()
            val activity = controller.get()
            val root = activity.findViewById<View>(android.R.id.content)
            root.button("1 draft awaiting approval").performClick()
            root.button("Content checklist").performClick()
            shadowOf(Looper.getMainLooper()).idle()
            val checklist = ShadowAlertDialog.getLatestAlertDialog() as AlertDialog
            checklist.window!!.decorView.descendants().filterIsInstance<EditText>().single().setText("Product photo")
            checklist.getButton(AlertDialog.BUTTON_POSITIVE).performClick()
            root.button("Back to dashboard").performClick()
            root.button("1 draft with missing content").performClick()
            assertTrue(root.descendants().filterIsInstance<TextView>().any { it.text == "Content needed · Product photo" })
            assertTrue(root.descendants().filterIsInstance<Button>().none { it.text == "Approve caption" })

            root.button("Image prompt").performClick()
            shadowOf(Looper.getMainLooper()).idle()
            val prompt = ShadowAlertDialog.getLatestAlertDialog() as AlertDialog
            val promptEditor = prompt.window!!.decorView.descendants().filterIsInstance<EditText>().single()
            assertTrue(promptEditor.text.contains(original.caption))
            promptEditor.setText("A close-up of the finished print")
            prompt.getButton(AlertDialog.BUTTON_NEUTRAL).performClick()
            val clipboard = activity.getSystemService(ClipboardManager::class.java)
            assertEquals("A close-up of the finished print", clipboard.primaryClip?.getItemAt(0)?.text)
            prompt.getButton(AlertDialog.BUTTON_POSITIVE).performClick()

            root.button("Content checklist").performClick()
            shadowOf(Looper.getMainLooper()).idle()
            val clear = ShadowAlertDialog.getLatestAlertDialog() as AlertDialog
            clear.window!!.decorView.descendants().filterIsInstance<EditText>().single().setText("")
            clear.getButton(AlertDialog.BUTTON_POSITIVE).performClick()
            root.button("Back to dashboard").performClick()
            root.tile("Needs approval").performClick()
            assertTrue(root.button("Approve caption").isShown)
            val saved = DraftStore(context).use { it.recent().single() }
            assertEquals(original.caption, saved.caption)
            assertEquals("A close-up of the finished print", saved.review.imagePrompt)
        }
    }

    @Test fun dashboardOpensEachExistingWorkspaceAndPrioritizesModelSetup() {
        Robolectric.buildActivity(MainActivity::class.java).setup().use { controller ->
            shadowOf(Looper.getMainLooper()).idle()
            val root = controller.get().findViewById<View>(android.R.id.content)
            val setup = root.button("Set up offline AI to generate drafts")
            assertTrue(setup.isShown)
            assertTrue(!root.button("Download offline AI · 1.6 GB").isShown)
            setup.performClick()
            assertTrue(root.button("Download offline AI · 1.6 GB").isShown)
            root.button("Back to dashboard").performClick()

            root.tile("Schedule").performClick()
            assertTrue(root.descendants().filterIsInstance<Switch>().single().isShown)
            assertTrue(root.button("Confirm regular store hours").isShown)
            controller.get().onBackPressed()

            root.tile("Campaign notes").performClick()
            assertTrue(root.button("Campaign notes and skips").isShown)
            root.button("Back to dashboard").performClick()
            assertTrue(root.tile("Offline AI").isShown)
        }
    }

    @Test fun olderApprovedDraftsAreReachableFromTheInbox() {
        val day = LocalDate.parse("2026-11-14")
        val timing = DraftTiming(Instant.parse("2026-11-14T15:08:00Z"), DraftOrigin.BACKGROUND)
        DraftStore(context).use { store ->
            for (offset in 0L..60L) {
                assertTrue(store.saveGenerated(Draft(day.minusDays(offset), Slot.MORNING,
                    "Caption $offset", timing), Campaign()))
            }
            val oldest = store.recent(61).last()
            assertTrue(store.setApproval(oldest, true))
        }
        Robolectric.buildActivity(MainActivity::class.java).setup().use { controller ->
            val root = controller.get().findViewById<View>(android.R.id.content)
            root.tile("Draft inbox").performClick()
            root.button("Show older drafts").performClick()
            assertTrue(root.button("Copy caption").isShown)
        }
    }

    private fun View.button(label: String): Button {
        val buttons = descendants().filterIsInstance<Button>().toList()
        return checkNotNull(buttons.singleOrNull { it.text == label }) {
            "Expected one '$label' button, found ${buttons.map { it.text }}"
        }
    }

    private fun View.tile(label: String): View =
        descendants().single { it.contentDescription?.startsWith("$label.") == true }

    private fun View.descendants(): Sequence<View> = sequence {
        yield(this@descendants)
        if (this@descendants is ViewGroup) {
            for (i in 0 until childCount) yieldAll(getChildAt(i).descendants())
        }
    }
}
