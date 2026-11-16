package com.belenos.bam

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import com.facebook.AccessToken
import com.facebook.CallbackManager
import com.facebook.FacebookCallback
import com.facebook.FacebookException
import com.facebook.FacebookSdk
import com.facebook.GraphRequest
import com.facebook.GraphRequestAsyncTask
import com.facebook.HttpMethod
import com.facebook.login.LoginManager
import com.facebook.login.LoginResult
import org.json.JSONObject

internal data class FacebookPage(val id: String, val name: String)

internal class FacebookPageList {
    private val pages = linkedMapOf<String, FacebookPage>()
    private val cursors = mutableSetOf<String>()

    fun read(response: JSONObject): String? {
        val data = response.getJSONArray("data")
        require(data.length() <= 50)
        for (index in 0 until data.length()) {
            val row = data.getJSONObject(index)
            val id = row.get("id") as? String ?: error("Missing Page ID")
            val name = (row.get("name") as? String)?.trim() ?: error("Missing Page name")
            require(id.matches(Regex("[0-9]{1,32}")) && name.isNotEmpty() && name.length <= 256)
            pages[id] = FacebookPage(id, name)
        }
        val paging = response.optJSONObject("paging")
        if (paging == null || !paging.has("next")) return null
        // Use only the cursor. A provider-supplied continuation URL cannot change the destination.
        val cursor = paging.getJSONObject("cursors").get("after") as? String
        require(!cursor.isNullOrBlank() && cursor.length <= 2048 && cursor.none(Char::isISOControl))
        require(cursors.size < 19 && cursors.add(cursor))
        return cursor
    }

    fun results(): List<FacebookPage> = pages.values.toList()
}

internal sealed interface FacebookDiscoveryResult {
    data class Pages(val pages: List<FacebookPage>) : FacebookDiscoveryResult
    enum class Error : FacebookDiscoveryResult { CANCELED, DENIED, EXPIRED, UNAVAILABLE }
}

internal class FacebookPageDiscovery(private val activity: Activity) {
    private val appId = activity.getString(R.string.bam_facebook_test_app_id)
    private val clientToken = activity.getString(R.string.bam_facebook_test_client_token)
    val configured = appId.isNotBlank() && clientToken.isNotBlank()
    private var callback: CallbackManager? = null
    private var loginManager: LoginManager? = null
    private var task: GraphRequestAsyncTask? = null
    private var completion: ((FacebookDiscoveryResult) -> Unit)? = null

    @Suppress("DEPRECATION")
    fun start(onComplete: (FacebookDiscoveryResult) -> Unit) {
        if (!configured || completion != null) return
        completion = onComplete
        try {
            if (!FacebookSdk.isInitialized()) {
                FacebookSdk.setApplicationId(appId)
                FacebookSdk.setClientToken(clientToken)
                FacebookSdk.sdkInitialize(activity.applicationContext)
            }
            val manager = LoginManager.getInstance().also { loginManager = it }
            manager.logOut()
            val callbacks = CallbackManager.Factory.create().also { callback = it }
            manager.registerCallback(callbacks, object : FacebookCallback<LoginResult> {
                override fun onSuccess(result: LoginResult) {
                    val token = result.accessToken
                    when {
                        token.isExpired || token.isDataAccessExpired ->
                            finish(FacebookDiscoveryResult.Error.EXPIRED)
                        PAGE_LIST_PERMISSION !in token.permissions ->
                            finish(FacebookDiscoveryResult.Error.DENIED)
                        else -> fetch(token, FacebookPageList(), null)
                    }
                }

                override fun onCancel() = finish(FacebookDiscoveryResult.Error.CANCELED)
                override fun onError(error: FacebookException) =
                    finish(FacebookDiscoveryResult.Error.UNAVAILABLE)
            })
            manager.logInWithReadPermissions(activity, listOf(PAGE_LIST_PERMISSION))
        } catch (_: RuntimeException) {
            finish(FacebookDiscoveryResult.Error.UNAVAILABLE)
        }
    }

    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean =
        callback?.onActivityResult(requestCode, resultCode, data) ?: false

    private fun fetch(token: AccessToken, pages: FacebookPageList, after: String?) {
        if (token.isExpired || token.isDataAccessExpired) {
            finish(FacebookDiscoveryResult.Error.EXPIRED)
            return
        }
        val params = Bundle().apply {
            putString("fields", "id,name")
            putString("limit", "50")
            if (after != null) putString("after", after)
        }
        task = GraphRequest(token, "me/accounts", params, HttpMethod.GET, callback = { response ->
            if (completion == null) return@GraphRequest
            task = null
            val error = response.error
            if (error != null) {
                finish(if (error.errorCode == 190) FacebookDiscoveryResult.Error.EXPIRED
                    else FacebookDiscoveryResult.Error.UNAVAILABLE)
                return@GraphRequest
            }
            val parsed = runCatching { pages.read(checkNotNull(response.jsonObject)) }
            parsed.fold(
                onSuccess = { cursor ->
                    if (cursor == null) finish(FacebookDiscoveryResult.Pages(pages.results()))
                    else fetch(token, pages, cursor)
                },
                onFailure = { finish(FacebookDiscoveryResult.Error.UNAVAILABLE) },
            )
        }).executeAsync()
    }

    private fun finish(result: FacebookDiscoveryResult) {
        val onComplete = completion
        close()
        onComplete?.invoke(result)
    }

    fun close() {
        completion = null
        task?.cancel(true)
        task = null
        callback?.let { loginManager?.unregisterCallback(it) }
        callback = null
        loginManager?.logOut()
        loginManager = null
    }

    companion object {
        const val PAGE_LIST_PERMISSION = "pages_show_list"
    }
}
