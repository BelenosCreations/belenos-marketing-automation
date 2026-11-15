package com.belenos.bam

import android.content.ContentProvider
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.database.Cursor
import android.database.MatrixCursor
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.provider.OpenableColumns
import java.io.FileNotFoundException
import java.time.LocalDate
import java.util.UUID

/**
 * Read-only, per-image Android share grant. No public gallery or broad file path is exposed.
 * Every receiver read checks the current draft revision, attached image and approval again.
 */
class DraftShareProvider : ContentProvider() {
    internal data class Reference(
        val day: LocalDate, val slot: Slot, val revision: Long, val imageId: String
    )

    companion object {
        internal fun uriFor(context: Context, draft: Draft): Uri? {
            val id = draft.review.imageId ?: return null
            if (draft.slot == Slot.SAMPLE || !draft.review.approved ||
                draft.review.contentNeeded.isNotEmpty()) return null
            return Uri.Builder().scheme("content")
                .authority("${context.packageName}.draftshare")
                .appendPath("image").appendPath(draft.day.toString())
                .appendPath(draft.slot.name).appendPath(draft.review.revision.toString())
                .appendPath(id).build()
        }

        internal fun shareIntent(context: Context, draft: Draft): Intent? {
            val uri = uriFor(context, draft) ?: return null
            return Intent(Intent.ACTION_SEND).apply {
                type = "image/*"
                putExtra(Intent.EXTRA_STREAM, uri)
                putExtra(Intent.EXTRA_TEXT, draft.caption)
                clipData = android.content.ClipData.newUri(context.contentResolver, "BAM approved image", uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
        }

        internal fun mime(bytes: ByteArray): String {
            if (bytes.size >= 8 && bytes.sliceArray(0..7).contentEquals(byteArrayOf(
                    0x89.toByte(), 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a))) return "image/png"
            if (bytes.size >= 3 && bytes[0] == 0xff.toByte() &&
                bytes[1] == 0xd8.toByte() && bytes[2] == 0xff.toByte()) return "image/jpeg"
            if (bytes.size >= 12 && String(bytes, 0, 4, Charsets.US_ASCII) == "RIFF" &&
                String(bytes, 8, 4, Charsets.US_ASCII) == "WEBP") return "image/webp"
            if (bytes.size >= 12 && String(bytes, 4, 4, Charsets.US_ASCII) == "ftyp") {
                val brand = String(bytes, 8, 4, Charsets.US_ASCII)
                if (brand in setOf("heic", "heix", "hevc", "hevx")) return "image/heic"
                if (brand in setOf("mif1", "msf1", "heim", "heis")) return "image/heif"
            }
            return "image/*"
        }
    }

    override fun onCreate(): Boolean = true

    private fun reference(uri: Uri): Reference? {
        if (uri.scheme != "content" || uri.authority != "${context?.packageName}.draftshare") return null
        val path = uri.pathSegments
        if (path.size != 5 || path[0] != "image") return null
        return runCatching {
            val day = LocalDate.parse(path[1])
            val slot = Slot.valueOf(path[2])
            val revision = path[3].toLong().also { require(it >= 0) }
            val imageId = UUID.fromString(path[4]).toString()
            Reference(day, slot, revision, imageId)
        }.getOrNull()
    }

    private fun approvedBytes(uri: Uri): ByteArray? {
        val ref = reference(uri) ?: return null
        return DraftStore(checkNotNull(context)).use {
            it.approvedImage(ref.day, ref.slot, ref.revision, ref.imageId)
        }
    }

    override fun getType(uri: Uri): String? = approvedBytes(uri)?.let(::mime)

    override fun query(uri: Uri, projection: Array<out String>?, selection: String?,
        selectionArgs: Array<out String>?, sortOrder: String?): Cursor? {
        val ref = reference(uri) ?: return null
        val bytes = approvedBytes(uri) ?: return null
        val columns = projection ?: arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE)
        if (columns.any { it != OpenableColumns.DISPLAY_NAME && it != OpenableColumns.SIZE }) return null
        val extension = when (mime(bytes)) {
            "image/png" -> "png"
            "image/jpeg" -> "jpg"
            "image/webp" -> "webp"
            "image/heic" -> "heic"
            "image/heif" -> "heif"
            else -> "image"
        }
        return MatrixCursor(columns).apply {
            val values = Array<Any>(columns.size) { index ->
                if (columns[index] == OpenableColumns.SIZE) bytes.size
                else "BAM-${ref.day}-${ref.slot.name.lowercase()}.$extension"
            }
            addRow(values)
        }
    }

    override fun openFile(uri: Uri, mode: String): ParcelFileDescriptor {
        if (mode != "r") throw FileNotFoundException("Read-only image share.")
        val bytes = approvedBytes(uri) ?: throw FileNotFoundException("Draft image is no longer approved.")
        val pipe = ParcelFileDescriptor.createPipe()
        Thread({
            try {
                ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]).use { it.write(bytes) }
            } catch (_: Exception) {
                // The receiving app may close the pipe before reading all bytes.
            }
        }, "bam-draft-share").apply { isDaemon = true }.start()
        return pipe[0]
    }

    override fun insert(uri: Uri, values: ContentValues?): Uri? =
        throw UnsupportedOperationException("Read-only image share.")

    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int =
        throw UnsupportedOperationException("Read-only image share.")

    override fun update(uri: Uri, values: ContentValues?, selection: String?,
        selectionArgs: Array<out String>?): Int =
        throw UnsupportedOperationException("Read-only image share.")
}
