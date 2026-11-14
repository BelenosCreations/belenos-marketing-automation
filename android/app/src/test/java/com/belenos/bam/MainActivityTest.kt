package com.belenos.bam

import android.app.Application
import android.content.ClipboardManager
import android.os.Looper
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
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
            assertTrue(root.descendants().filterIsInstance<TextView>().any {
                it.text == "Periodic background check · saved 10:08 AM ET · 8 min after target"
            })

            root.button("Edit caption").performClick()
            val dialog = ShadowAlertDialog.getLatestAlertDialog() as android.app.AlertDialog
            val editor = dialog.window!!.decorView.descendants().filterIsInstance<EditText>().single()
            editor.setText(" ")
            dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE).performClick()
            assertEquals("Enter a caption.", editor.error.toString())
            editor.setText("Edited caption for Facebook")
            dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE).performClick()

            root.button("Copy caption").performClick()
            val clipboard = activity.getSystemService(ClipboardManager::class.java)
            assertEquals("Edited caption for Facebook", clipboard.primaryClip?.getItemAt(0)?.text)
            assertEquals(timing, DraftStore(context).use { it.recent().single().timing })
        }
    }

    private fun View.button(label: String): Button =
        descendants().filterIsInstance<Button>().single { it.text == label }

    private fun View.descendants(): Sequence<View> = sequence {
        yield(this@descendants)
        if (this@descendants is ViewGroup) {
            for (i in 0 until childCount) yieldAll(getChildAt(i).descendants())
        }
    }
}
