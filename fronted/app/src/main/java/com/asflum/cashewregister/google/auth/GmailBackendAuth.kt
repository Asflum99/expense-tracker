package com.asflum.cashewregister.google.auth

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
    sealed class AuthStatus(val label: String) {
        object Authenticated : AuthStatus("authenticated")
        object Unauthenticated : AuthStatus("unauthenticated")
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()
    private const val API_URL = BuildConfig.API_URL

    suspend fun setupGmailAccess(
        context: Context,
        idToken: String
    ): Result<String> {
        return try {
            withContext(Dispatchers.IO) {
                when (isUserAlreadyAuth(idToken)) {
                    is AuthStatus.Authenticated -> {
                        Result.success(AuthStatus.Authenticated.label)
                    }

                    is AuthStatus.Unauthenticated -> {
                        authNewUser(context, idToken)
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Result.failure(e)
        }
    }

    private fun isUserAlreadyAuth(idToken: String): AuthStatus {
        val request = createRequest(idToken, "status")

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IOException("Error de conexión. Intente de nuevo.")
            }

            val responseBody = response.body.string()
            val success = JSONObject(responseBody).getBoolean("authenticated")
            if (!success) {
                return AuthStatus.Unauthenticated
            }
            return AuthStatus.Authenticated
        }
    }

    private suspend fun authNewUser(
        context: Context,
        idToken: String
    ): Result<String> = suspendCoroutine { continuation ->
        val request = createRequest(idToken, "google")

        try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    throw IOException("Error de conexión. Intente de nuevo.")
                }

                val responseBody = response.body.string()
                val jsonResponse = JSONObject(responseBody)
                val authUrl = jsonResponse.getString("auth_url")

                val receiver = object : BroadcastReceiver() {
                    override fun onReceive(ctx: Context?, intent: Intent?) {
                        continuation.resume(Result.success(AuthStatus.Authenticated.label))
                        LocalBroadcastManager.getInstance(context).unregisterReceiver(this)
                    }
                }
                LocalBroadcastManager.getInstance(context)
                    .registerReceiver(receiver, IntentFilter("cashew.AUTH_COMPLETE"))

                val customTabsIntent = CustomTabsIntent.Builder().build()
                customTabsIntent.launchUrl(context, authUrl.toUri())
            }
        } catch (e: Exception) {
            continuation.resume(Result.failure(e))
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