package com.belenos.bam

import android.graphics.Bitmap
import android.graphics.ImageDecoder
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.nio.ByteBuffer
import kotlin.math.roundToInt

internal class DraftImage private constructor(val original: ByteArray, val thumbnail: ByteArray) {
    companion object {
        internal const val MAX_BYTES = 16 * 1024 * 1024
        private const val PREVIEW_EDGE = 320
        private val supportedTypes = setOf("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif")

        fun read(input: InputStream): DraftImage {
            val bytes = ByteArrayOutputStream()
            val buffer = ByteArray(32 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                require(count > 0) { "Could not read the selected image." }
                require(bytes.size() + count <= MAX_BYTES) { "Choose an image under 16 MB." }
                bytes.write(buffer, 0, count)
            }
            val original = bytes.toByteArray()
            require(original.isNotEmpty()) { "The selected image is empty." }
            val bitmap = ImageDecoder.decodeBitmap(ImageDecoder.createSource(ByteBuffer.wrap(original))) {
                decoder, info, _ ->
                require(info.mimeType in supportedTypes) { "Choose a JPEG, PNG, WebP, or HEIF image." }
                val width = info.size.width
                val height = info.size.height
                require(width > 0 && height > 0 && width.toLong() * height <= 200_000_000) {
                    "The selected image is too large to preview."
                }
                val scale = minOf(1.0, PREVIEW_EDGE.toDouble() / maxOf(width, height))
                decoder.setTargetSize((width * scale).roundToInt().coerceAtLeast(1),
                    (height * scale).roundToInt().coerceAtLeast(1))
                decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            }
            try {
                val preview = ByteArrayOutputStream()
                check(bitmap.compress(Bitmap.CompressFormat.PNG, 100, preview))
                return DraftImage(original, preview.toByteArray())
            } finally {
                bitmap.recycle()
            }
        }
    }
}
