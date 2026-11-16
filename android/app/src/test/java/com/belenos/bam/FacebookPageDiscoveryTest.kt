package com.belenos.bam

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class FacebookPageDiscoveryTest {
    @Test fun readsNamesAndIdsAcrossPagesWithoutFollowingProviderUrls() {
        val listing = FacebookPageList()
        assertEquals("cursor-1", listing.read(JSONObject("""
            {"data":[{"id":"12","name":"Belenos Creations","access_token":"unused"}],
             "paging":{"next":"https://example.invalid/redirect","cursors":{"after":"cursor-1"}}}
        """)))
        assertNull(listing.read(JSONObject("""
            {"data":[{"id":"12","name":"Belenos Creations"},{"id":"92","name":"Busy B Cleaning Service"}]}
        """)))
        assertEquals(listOf(FacebookPage("12", "Belenos Creations"),
            FacebookPage("92", "Busy B Cleaning Service")), listing.results())
    }

    @Test fun acceptsAnEmptyAuthorizedList() {
        val listing = FacebookPageList()
        assertNull(listing.read(JSONObject("""{"data":[]}""")))
        assertTrue(listing.results().isEmpty())
    }

    @Test fun rejectsRepeatedCursorsAndMalformedPageRows() {
        val listing = FacebookPageList()
        val repeated = JSONObject("""{"data":[],"paging":{"next":"url","cursors":{"after":"same"}}}""")
        assertEquals("same", listing.read(repeated))
        assertTrue(runCatching { listing.read(repeated) }.isFailure)
        assertTrue(runCatching {
            listing.read(JSONObject("""{"data":[{"id":"untrusted","name":"Some Page"}]}"""))
        }.isFailure)
        assertTrue(runCatching {
            listing.read(JSONObject("""{"data":[],"paging":{"next":"url"}}"""))
        }.isFailure)
    }
}
