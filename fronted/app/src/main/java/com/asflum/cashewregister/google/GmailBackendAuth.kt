package com.asflum.cashewregister.google

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import androidx.browser.customtabs.CustomTabsIntent
import androidx.core.net.toUri
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import com.asflum.cashewregister.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okio.IOException
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine

object GmailBackendAuth {
    enum class AuthStatus {
        AUTHENTICATED,
        UNAUTHENTICATED,
        ERROR
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()
    private const val BACKEND_URL = BuildConfig.BACKEND_URL

    suspend fun setupGmailAccess(
        context: Context,
        idToken: String
    ): Boolean {
        return withContext(Dispatchers.IO) {
            when (isUserAlreadyAuth(idToken)) {
                AuthStatus.AUTHENTICATED -> {
                    true
                }

                AuthStatus.UNAUTHENTICATED -> {
                    authNewUser(context, idToken)
                }

                AuthStatus.ERROR -> {
                    false
                }
            }
        }
    }

    private fun isUserAlreadyAuth(idToken: String): AuthStatus {
        val request = createRequest(idToken, "status")

        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    return AuthStatus.ERROR
                }
                val responseBody = response.body.string()

                try {
                    val success = JSONObject(responseBody).getBoolean("authenticated")
                    if (!success) {
                        return AuthStatus.UNAUTHENTICATED
                    }
                    AuthStatus.AUTHENTICATED
                } catch (e: Exception) {
                    e.printStackTrace()
                    AuthStatus.ERROR
                }
            }
        } catch (e: IOException) {
            e.printStackTrace()
            AuthStatus.ERROR
        }
    }

    private suspend fun authNewUser(
        context: Context,
        idToken: String
    ): Boolean = suspendCoroutine { continuation ->
        val request = createRequest(idToken, "google")

        try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    continuation.resumeWithException(IOException("Auth failed"))
                    return@use
                }

                val responseBody = response.body.string()
                val jsonResponse = JSONObject(responseBody)

                val authUrl = jsonResponse.getString("auth_url")

                // ✅ Registrar primero el receiver
                val receiver = object : BroadcastReceiver() {
                    override fun onReceive(ctx: Context?, intent: Intent?) {
                        continuation.resume(true)
                        LocalBroadcastManager.getInstance(context).unregisterReceiver(this)
                    }
                }
                LocalBroadcastManager.getInstance(context)
                    .registerReceiver(receiver, IntentFilter("cashew.AUTH_COMPLETE"))

                // ✅ Luego lanzar el navegador
                val customTabsIntent = CustomTabsIntent.Builder().build()
                customTabsIntent.launchUrl(context, authUrl.toUri())
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    private fun createRequest(idToken: String, task: String): Request {
        val json = JSONObject().apply {
            put("id_token", idToken)
        }

        val requestBody = json.toString().toRequestBody("application/json".toMediaType())
        return Request.Builder()
            .url("${BACKEND_URL}/users/auth/$task")
            .post(requestBody)
            .build()
    }
}