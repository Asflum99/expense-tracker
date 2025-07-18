package com.asflum.cashewregister

import android.content.Context
import android.util.Log
import androidx.browser.customtabs.CustomTabsIntent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import androidx.core.net.toUri
import androidx.core.content.edit

object BackendConnection {
    private val client = OkHttpClient()
    private const val NGROKURL = BuildConfig.BACKEND_URL
    suspend fun sendTokenToBackend(context: Context, idToken: String, client: OkHttpClient, ngrokUrl: String): Boolean {
        return withContext(Dispatchers.IO) {
            try {
                val jsonString = """
                    {
                        "id_token": "$idToken"
                    }
                """.trimIndent()

                val requestBody = jsonString.toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url("${ngrokUrl}/users/auth/google")
                    .post(requestBody)
                    .addHeader("ngrok-skip-browser-warning", "true")
                    .build()

                val response = client.newCall(request).execute()

                if (!response.isSuccessful) {
                    val errorBody = response.body.string()
                    Log.e("Backend", "Error response: $errorBody")
                    return@withContext false
                }

                val responseBody = response.body.string()
                val json = JSONObject(responseBody)
                val userId = json.getString("userid")

                UserPrefs.saveUserId(context, userId)
                true
            } catch (e: Exception) {
                Log.e("Backend", "Error enviando token", e)
                false
            }
        }
    }

    fun sendIdTokenToBackend(context: Context, idToken: String): Boolean {
        return try {
            val json = JSONObject().apply {
                put("id_token", idToken)
            }

            val requestBody = json.toString().toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url("${NGROKURL}/users/auth/google")
                .post(requestBody)
                .build()

            val response = client.newCall(request).execute()
            val responseBody = response.body.string()

            if (!response.isSuccessful) {
                Log.e("Backend", "Error response: $responseBody")
                return false
            }

            val jsonResponse = JSONObject(responseBody)
            val authUrl = jsonResponse.getString("auth_url")

            val prefs = context.getSharedPreferences("auth", Context.MODE_PRIVATE)
            prefs.edit { putBoolean("auth_complete", false) }
            val customTabsIntent = CustomTabsIntent.Builder().build()
            customTabsIntent.launchUrl(context, authUrl.toUri())

            while (!prefs.getBoolean("auth_complete", false)) {
                Thread.sleep(300)
            }

            true
        } catch (e: Exception) {
            Log.e("Backend", "Error enviando token", e)
            false
        }
    }
}