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
import kotlin.coroutines.suspendCoroutine

object GmailBackendAuth {
    sealed class AuthStatus {
        object Authenticated : AuthStatus()
        object Unauthenticated : AuthStatus()
        data class Error(val message: String?) : AuthStatus()
    }

    data class AuthResult(val success: Boolean, val error: String? = null) {
        val isSuccess: Boolean get() = success && error == null
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()
    private const val API_URL = BuildConfig.API_URL

    suspend fun setupGmailAccess(
        context: Context,
        idToken: String
    ): AuthResult {
        return withContext(Dispatchers.IO) {
            when (val status = isUserAlreadyAuth(idToken)) {
                is AuthStatus.Authenticated -> {
                    AuthResult(true)
                }

                is AuthStatus.Unauthenticated -> {
                    authNewUser(context, idToken)
                }

                is AuthStatus.Error -> {
                    AuthResult(false, status.message)
                }
            }
        }
    }

    private fun isUserAlreadyAuth(idToken: String): AuthStatus {
        val request = createRequest(idToken, "status")

        return try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorMessage = response.body.string()
                    return AuthStatus.Error(errorMessage)
                }
                val responseBody = response.body.string()

                try {
                    val success = JSONObject(responseBody).getBoolean("authenticated")
                    if (!success) {
                        return AuthStatus.Unauthenticated
                    }
                    AuthStatus.Authenticated
                } catch (e: Exception) {
                    e.printStackTrace()
                    AuthStatus.Error(e.message)
                }
            }
        } catch (e: IOException) {
            e.printStackTrace()
            AuthStatus.Error(e.message)
        }
    }

    private suspend fun authNewUser(
        context: Context,
        idToken: String
    ): AuthResult = suspendCoroutine { continuation ->
        val request = createRequest(idToken, "google")

        try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorMessage = response.body.string()
                    continuation.resume(AuthResult(false, errorMessage))
                    return@use
                }

                val responseBody = response.body.string()
                val jsonResponse = JSONObject(responseBody)
                val authUrl = jsonResponse.getString("auth_url")

                val receiver = object : BroadcastReceiver() {
                    override fun onReceive(ctx: Context?, intent: Intent?) {
                        continuation.resume(AuthResult(true))
                        LocalBroadcastManager.getInstance(context).unregisterReceiver(this)
                    }
                }
                LocalBroadcastManager.getInstance(context)
                    .registerReceiver(receiver, IntentFilter("cashew.AUTH_COMPLETE"))

                val customTabsIntent = CustomTabsIntent.Builder().build()
                customTabsIntent.launchUrl(context, authUrl.toUri())
            }
        } catch (e: Exception) {
            e.printStackTrace()
            continuation.resume(AuthResult(false, e.message ?: "Unexpected error"))
        }
    }

    private fun createRequest(idToken: String, task: String): Request {
        val json = JSONObject().apply {
            put("id_token", idToken)
        }

        val requestBody = json.toString().toRequestBody("application/json".toMediaType())
        return Request.Builder()
            .url("${API_URL}/users/auth/$task")
            .post(requestBody)
            .build()
    }
}