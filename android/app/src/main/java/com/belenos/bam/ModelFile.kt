package com.belenos.bam

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import java.io.File
import java.security.MessageDigest

class ModelFile internal constructor(
    private val context: Context,
    private val expectedSize: Long,
    private val expectedHash: String
) {
    constructor(context: Context) : this(context, SIZE, SHA256)

    private val settings = context.getSharedPreferences("bam", Context.MODE_PRIVATE)
    private val downloads = context.getSystemService(DownloadManager::class.java)
    private val directory = context.getExternalFilesDir(null)

    val file: File?
        get() = directory?.let { File(it, NAME) }

    fun ready(): Boolean = settings.getBoolean("verified_model_v1", false) &&
        file?.length() == expectedSize

    fun downloading(): Boolean = settings.contains("download")

    fun start() {
        check(!downloading())
        val model = checkNotNull(file) { "Storage is unavailable." }
        check(model.parentFile!!.usableSpace > expectedSize + 300_000_000L) {
            "Free up about 2 GB before downloading."
        }
        if (model.exists()) check(model.delete()) { "Could not replace the incomplete download." }
        val request = DownloadManager.Request(Uri.parse(URL))
            .setTitle("BAM on-device AI model")
            .setDescription("One-time download for offline drafting")
            .setAllowedOverMetered(false)
            .setAllowedOverRoaming(false)
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalFilesDir(context, null, NAME)
        val id = downloads.enqueue(request)
        settings.edit().putLong("download", id).putBoolean("verified_model_v1", false).apply()
    }

    // Called off the UI thread. The model is opened only after a full integrity check.
    fun checkDownload(): String? {
        val id = settings.getLong("download", -1)
        if (id == -1L) return null
        val status = downloads.query(DownloadManager.Query().setFilterById(id)).use { cursor ->
            if (cursor.moveToFirst()) cursor.getInt(cursor.getColumnIndexOrThrow(
                DownloadManager.COLUMN_STATUS)) else DownloadManager.STATUS_FAILED
        }
        if (status != DownloadManager.STATUS_SUCCESSFUL && status != DownloadManager.STATUS_FAILED) {
            return "Model download pending. Use Wi-Fi and keep about 2 GB free."
        }
        val model = file
        val verified = status == DownloadManager.STATUS_SUCCESSFUL && model != null &&
            model.length() == expectedSize && runCatching { digest(model) == expectedHash }.getOrDefault(false)
        settings.edit().remove("download").putBoolean("verified_model_v1", verified).commit()
        if (verified) return null
        downloads.remove(id)
        model?.delete()
        return "Model download failed verification. Try downloading again."
    }

    private fun digest(file: File): String {
        val hash = MessageDigest.getInstance("SHA-256")
        file.inputStream().buffered().use { stream ->
            val buffer = ByteArray(128 * 1024)
            while (true) {
                val length = stream.read(buffer)
                if (length == -1) break
                hash.update(buffer, 0, length)
            }
        }
        return hash.digest().joinToString("") { "%02x".format(it) }
    }

    companion object {
        private const val NAME = "qwen-1.5b-q8-v1.litertlm"
        private const val SIZE = 1597922856L
        private const val SHA256 = "c4a9b7289365ab80fe599b844b77ad253eb3c53fb0e5d963d699146a6f01255e"
        private const val URL = "https://huggingface.co/litert-community/Qwen2.5-1.5B-Instruct/" +
            "resolve/60257f9f1d00ca1f24cc5ce3b829b4139be1ca2b/" +
            "Qwen2.5-1.5B-Instruct_multi-prefill-seq_q8_ekv4096.litertlm"
    }
}
