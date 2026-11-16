package com.belenos.bam

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.net.Uri
import android.provider.OpenableColumns
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import java.io.ByteArrayOutputStream
import java.io.FileNotFoundException
import java.time.Instant
import java.time.LocalDate
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class DraftShareProviderTest {
    private lateinit var context: Context
    private val day = LocalDate.parse("2026-11-14")
    private val timing = DraftTiming(Instant.parse("2026-11-14T15:08:00Z"), DraftOrigin.BACKGROUND)

    @Before fun setUp() {
        context = RuntimeEnvironment.getApplication()
        context.deleteDatabase("drafts.db")
    }

    @Test fun sharesOnlyTheApprovedCurrentImageAndRevokesStaleUris() {
        val bytes = png(Color.BLUE)
        val draft = Draft(day, Slot.MORNING, "Approved caption", timing)
        val approved = DraftStore(context).use { store ->
            assertTrue(store.saveGenerated(draft, Campaign()))
            assertTrue(store.setImage(draft, DraftImage.read(bytes.inputStream())))
            val attachment = checkNotNull(store.find(day, Slot.MORNING))
            assertNull(DraftShareProvider.uriFor(context, attachment))
            assertFalse(store.canShareImage(attachment))
            assertTrue(store.setApproval(attachment, true))
            checkNotNull(store.find(day, Slot.MORNING))
        }
        val uri = checkNotNull(DraftShareProvider.uriFor(context, approved))
        val share = checkNotNull(DraftShareProvider.shareIntent(context, approved))
        assertEquals(Intent.ACTION_SEND, share.action)
        assertEquals("image/*", share.type)
        assertEquals(uri, share.getParcelableExtra(Intent.EXTRA_STREAM, android.net.Uri::class.java))
        assertEquals("Approved caption", share.getStringExtra(Intent.EXTRA_TEXT))
        assertEquals(uri, share.clipData?.getItemAt(0)?.uri)
        assertTrue(share.flags and Intent.FLAG_GRANT_READ_URI_PERMISSION != 0)
        assertEquals("image/png", context.contentResolver.getType(uri))
        context.contentResolver.query(uri, null, null, null, null).use { cursor ->
            assertNotNull(cursor)
            assertTrue(checkNotNull(cursor).moveToFirst())
            assertEquals(bytes.size.toLong(), cursor.getLong(cursor.getColumnIndexOrThrow(OpenableColumns.SIZE)))
            assertTrue(cursor.getString(cursor.getColumnIndexOrThrow(OpenableColumns.DISPLAY_NAME)).endsWith(".png"))
        }
        assertArrayEquals(bytes, readApprovedImage(uri, bytes.size))
        DraftStore(context).use { store ->
            assertTrue(store.edit(approved, "Edited and requires reapproval"))
            assertFalse(store.canShareImage(approved))
        }
        assertNull(context.contentResolver.getType(uri))
        assertThrows(FileNotFoundException::class.java) { context.contentResolver.openInputStream(uri) }
    }

    @Test fun imageReplacementNeedsFreshApprovalAndNeverSharesOldBytes() {
        val first = png(Color.RED)
        val replacement = png(Color.GREEN)
        val original = Draft(day, Slot.EVENING, "A post", timing)
        DraftStore(context).use { store ->
            assertTrue(store.saveGenerated(original, Campaign()))
            assertTrue(store.setImage(original, DraftImage.read(first.inputStream())))
            assertTrue(store.setApproval(checkNotNull(store.find(day, Slot.EVENING)), true))
        }
        val firstApproved = DraftStore(context).use { checkNotNull(it.find(day, Slot.EVENING)) }
        val oldUri = checkNotNull(DraftShareProvider.uriFor(context, firstApproved))
        DraftStore(context).use { store ->
            assertTrue(store.setImage(firstApproved, DraftImage.read(replacement.inputStream())))
            val pending = checkNotNull(store.find(day, Slot.EVENING))
            assertNull(DraftShareProvider.uriFor(context, pending))
            assertNull(store.approvedImage(firstApproved.day, firstApproved.slot,
                firstApproved.review.revision, checkNotNull(firstApproved.review.imageId)))
            assertTrue(store.setApproval(pending, true))
        }
        assertThrows(FileNotFoundException::class.java) { context.contentResolver.openInputStream(oldUri) }
        val fresh = DraftStore(context).use { checkNotNull(it.find(day, Slot.EVENING)) }
        val current = checkNotNull(DraftShareProvider.uriFor(context, fresh))
        assertArrayEquals(replacement, readApprovedImage(current, replacement.size))
        DraftStore(context).use { store -> assertTrue(store.setImage(fresh, null)) }
        assertThrows(FileNotFoundException::class.java) { context.contentResolver.openInputStream(current) }
    }

    @Test fun shareButtonOpensChooserForOneImageWithoutPublishing() {
        val original = Draft(day, Slot.MORNING, "Use my caption", timing)
        DraftStore(context).use { store ->
            assertTrue(store.saveGenerated(original, Campaign()))
            assertTrue(store.setImage(original, DraftImage.read(png(Color.YELLOW).inputStream())))
            assertTrue(store.setApproval(checkNotNull(store.find(day, Slot.MORNING)), true))
        }
        Robolectric.buildActivity(MainActivity::class.java).setup().use { controller ->
            val activity = controller.get()
            val root = activity.findViewById<View>(android.R.id.content)
            root.descendants().single { it.contentDescription?.startsWith("Draft inbox.") == true }
                .performClick()
            root.button("Share approved image").performClick()
            val chooser = shadowOf(activity).nextStartedActivity
            assertEquals(Intent.ACTION_CHOOSER, chooser.action)
            val target = chooser.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
            assertEquals(Intent.ACTION_SEND, target?.action)
            assertEquals(ClipData.newUri(context.contentResolver, "BAM approved image",
                checkNotNull(target?.getParcelableExtra(Intent.EXTRA_STREAM, android.net.Uri::class.java)))
                .itemCount, target.clipData?.itemCount)
        }
    }

    @Test fun sampleAndForgedOrUnapprovedUrisCannotBeRead() {
        val sample = Draft(day, Slot.SAMPLE, "Test", timing)
        DraftStore(context).use { store ->
            assertTrue(store.saveGenerated(sample, Campaign()))
            assertTrue(store.setImage(sample, DraftImage.read(png(Color.MAGENTA).inputStream())))
            val draft = checkNotNull(store.find(day, Slot.SAMPLE))
            assertNull(DraftShareProvider.uriFor(context, draft))
            assertNull(store.approvedImage(day, Slot.SAMPLE, draft.review.revision,
                checkNotNull(draft.review.imageId)))
        }
        val forged = android.net.Uri.parse("content://${context.packageName}.draftshare/image/2026-11-14/MORNING/0/not-a-uuid")
        assertNull(context.contentResolver.getType(forged))
        assertThrows(FileNotFoundException::class.java) { context.contentResolver.openInputStream(forged) }
    }

    private fun readApprovedImage(uri: Uri, expectedSize: Int): ByteArray {
        val deadline = System.nanoTime() + 2_000_000_000L
        return checkNotNull(context.contentResolver.openInputStream(uri)).use { stream ->
            val bytes = ByteArrayOutputStream()
            do {
                bytes.write(stream.readBytes())
                if (bytes.size() >= expectedSize) break
                // Robolectric's file-backed pipe can reach EOF before the writer thread runs.
                Thread.sleep(5)
            } while (System.nanoTime() < deadline)
            bytes.toByteArray()
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

    private fun png(color: Int): ByteArray {
        val bitmap = Bitmap.createBitmap(32, 32, Bitmap.Config.ARGB_8888)
        bitmap.eraseColor(color)
        return ByteArrayOutputStream().use {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
            bitmap.recycle()
            it.toByteArray()
        }
    }
}
