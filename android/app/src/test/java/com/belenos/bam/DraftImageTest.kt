package com.belenos.bam

import android.app.Activity
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.provider.MediaStore
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.time.Instant
import java.time.LocalDate
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Robolectric
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class DraftImageTest {
    private lateinit var context: Context
    private val day = LocalDate.parse("2026-11-14")
    private val timing = DraftTiming(Instant.parse("2026-11-14T15:08:00Z"), DraftOrigin.BACKGROUND)

    @Before fun setUp() {
        context = RuntimeEnvironment.getApplication()
        context.deleteDatabase("drafts.db")
    }

    @Test fun attachmentReplacementAndRemovalPreserveCaptionAndInvalidateApproval() {
        val original = Draft(day, Slot.MORNING, "Original caption", timing)
        val bytes = makeImage(Color.TRANSPARENT)
        val image = DraftImage.read(bytes.inputStream())
        assertArrayEquals(bytes, image.original)
        val thumbnail = BitmapFactory.decodeByteArray(image.thumbnail, 0, image.thumbnail.size)
        assertEquals(320, thumbnail.width)
        assertEquals(160, thumbnail.height)
        assertEquals(Color.TRANSPARENT, thumbnail.getPixel(10, 10))
        thumbnail.recycle()

        val firstId = DraftStore(context).use { store ->
            assertTrue(store.saveGenerated(original, Campaign()))
            assertTrue(store.setApproval(original, true))
            val approved = checkNotNull(store.find(day, Slot.MORNING))
            assertTrue(store.setImage(approved, image))
            assertFalse(store.setImage(approved, null))
            val attached = store.recent(queue = DraftQueue.NEEDS_APPROVAL).single()
            assertEquals(original.caption, attached.caption)
            assertEquals(original.timing, attached.timing)
            checkNotNull(attached.review.imageId)
        }

        DraftStore(context).use { store ->
            val attached = checkNotNull(store.find(day, Slot.MORNING))
            assertArrayEquals(image.thumbnail, store.thumbnail(firstId))
            store.readableDatabase.rawQuery("SELECT original FROM draft_image WHERE id=?", arrayOf(firstId)).use {
                assertTrue(it.moveToFirst())
                assertArrayEquals(bytes, it.getBlob(0))
            }
            val replacement = DraftImage.read(makeImage(Color.BLUE).inputStream())
            assertTrue(store.setImage(attached, replacement))
            val replaced = checkNotNull(store.find(day, Slot.MORNING))
            val replacementId = checkNotNull(replaced.review.imageId)
            assertNotEquals(firstId, replacementId)
            assertNull(store.thumbnail(firstId))
            assertArrayEquals(replacement.thumbnail, store.thumbnail(replacementId))
            assertTrue(store.setImage(replaced, null))
            val removed = checkNotNull(store.find(day, Slot.MORNING))
            assertEquals(original.caption, removed.caption)
            assertNull(removed.review.imageId)
            assertNull(store.thumbnail(replacementId))
        }
    }

    @Test fun sampleRegenerationDiscardsItsOldImageAndInvalidatesPickerRevision() {
        val sample = Draft(day, Slot.SAMPLE, "Sample", timing)
        val image = DraftImage.read(makeImage(Color.RED).inputStream())
        DraftStore(context).use { store ->
            assertTrue(store.saveGenerated(sample, Campaign()))
            assertTrue(store.setImage(sample, image))
            val attached = checkNotNull(store.find(day, Slot.SAMPLE))
            assertTrue(store.saveGenerated(sample, Campaign()))
            val newSample = checkNotNull(store.find(day, Slot.SAMPLE))
            assertTrue(newSample.review.revision > attached.review.revision)
            assertNull(newSample.review.imageId)
            assertNull(store.thumbnail(checkNotNull(attached.review.imageId)))
            assertFalse(store.setImage(attached, image))
        }
    }

    @Test fun rejectsEmptyCorruptAndOversizedImages() {
        assertThrows(IllegalArgumentException::class.java) { DraftImage.read(byteArrayOf().inputStream()) }
        assertThrows(Exception::class.java) { DraftImage.read("not an image".byteInputStream()) }
        val oversized = object : InputStream() {
            var remaining = DraftImage.MAX_BYTES + 1
            override fun read(): Int = error("Expected buffered read")
            override fun read(b: ByteArray, off: Int, len: Int): Int {
                if (remaining == 0) return -1
                val count = minOf(remaining, len)
                remaining -= count
                return count
            }
        }
        assertThrows(IllegalArgumentException::class.java) { DraftImage.read(oversized) }
    }

    @Test fun replacingViaSystemPickerCanBeCanceledWithoutLosingThePreview() {
        val sample = Draft(day, Slot.SAMPLE, "Sample", timing)
        DraftStore(context).use { store ->
            assertTrue(store.saveGenerated(sample, Campaign()))
            assertTrue(store.setImage(sample, DraftImage.read(makeImage(Color.BLUE).inputStream())))
        }
        Robolectric.buildActivity(MainActivity::class.java).setup().use { controller ->
            val activity = controller.get()
            val root = activity.findViewById<View>(android.R.id.content)
            root.descendants().single { it.contentDescription?.startsWith("Draft inbox.") == true }.performClick()
            assertTrue(root.descendants().filterIsInstance<ImageView>().any {
                it.contentDescription == "Attached draft image" && it.drawable != null
            })
            root.button("Replace image").performClick()
            val picker = shadowOf(activity).nextStartedActivityForResult.intent
            assertEquals(MediaStore.ACTION_PICK_IMAGES, picker.action)
            assertEquals("image/*", picker.type)
            shadowOf(activity).receiveResult(picker, Activity.RESULT_CANCELED, null)
            root.button("Remove image").performClick()
            assertTrue(root.button("Attach image").isShown)
            assertNull(DraftStore(context).use { it.find(day, Slot.SAMPLE)?.review?.imageId })
        }
    }

    private fun View.button(label: String): Button =
        descendants().filterIsInstance<Button>().single { it.text == label }

    private fun View.descendants(): Sequence<View> = sequence {
        yield(this@descendants)
        if (this@descendants is ViewGroup) {
            for (index in 0 until childCount) yieldAll(getChildAt(index).descendants())
        }
    }

    private fun makeImage(color: Int): ByteArray {
        val bitmap = Bitmap.createBitmap(640, 320, Bitmap.Config.ARGB_8888)
        bitmap.eraseColor(color)
        return ByteArrayOutputStream().use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
            bitmap.recycle()
            it.toByteArray()
        }
    }
}
