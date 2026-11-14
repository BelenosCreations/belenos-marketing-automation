package com.belenos.bam

import android.app.DownloadManager
import android.content.Context
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment.getApplication
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.shadow.api.Shadow
import org.robolectric.shadows.ShadowDownloadManager.ShadowRequest

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class ModelFileTest {
    private val context by lazy { getApplication() }
    private val settings by lazy { context.getSharedPreferences("bam", Context.MODE_PRIVATE) }
    private val downloads by lazy { context.getSystemService(DownloadManager::class.java) }
    private val model by lazy { fixtureModel() }
    private val path get() = checkNotNull(model.file)

    @Before fun setUp() {
        settings.edit().clear().commit()
        path.delete()
    }

    @Test fun downloadPersistsAndWaitsForVerificationAfterReopening() {
        model.start()
        val request = currentRequest()
        assertEquals("https", request.uri.scheme)
        assertEquals(path, java.io.File(checkNotNull(request.destination.path)))
        assertFalse(request.allowedOverMetered)
        assertFalse(request.allowedOverRoaming)
        assertThrows(IllegalStateException::class.java) { model.start() }

        path.writeText("hello")
        request.status = DownloadManager.STATUS_RUNNING
        val reopened = fixtureModel()
        assertTrue(reopened.downloading())
        assertFalse(reopened.ready())
        assertTrue(checkNotNull(reopened.checkDownload()).contains("pending"))
        assertFalse(reopened.ready())

        request.status = DownloadManager.STATUS_SUCCESSFUL
        assertNull(reopened.checkDownload())
        assertFalse(fixtureModel().downloading())
        assertTrue(fixtureModel().ready())
        path.writeText("hell")
        assertFalse(fixtureModel().ready())
    }

    @Test fun wrongHashAndTruncatedFilesStayUnavailableAndAllowRetry() {
        for (contents in listOf("world", "hell")) {
            model.start()
            path.writeText(contents)
            currentRequest().status = DownloadManager.STATUS_SUCCESSFUL
            assertFailedAndCleared()
        }
        assertEquals(0, shadowOf(downloads).requestCount)
    }

    @Test fun failedAndMissingDownloadRecordsAllowRetry() {
        model.start()
        path.writeText("hell")
        currentRequest().status = DownloadManager.STATUS_FAILED
        assertFailedAndCleared()

        model.start()
        downloads.remove(settings.getLong("download", -1))
        assertFailedAndCleared()
    }

    private fun assertFailedAndCleared() {
        assertTrue(checkNotNull(model.checkDownload()).contains("Try downloading again"))
        assertFalse(model.ready())
        assertFalse(model.downloading())
        assertFalse(path.exists())
    }

    private fun currentRequest(): ShadowRequest =
        Shadow.extract(checkNotNull(shadowOf(downloads).getRequest(settings.getLong("download", -1))))

    private fun fixtureModel() = ModelFile(context, 5,
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
}
