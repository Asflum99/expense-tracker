package com.asflum.cashewregister

import android.content.Context
import android.util.Log
import android.widget.Toast
import androidx.browser.customtabs.CustomTabsIntent
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import androidx.core.net.toUri
import androidx.core.content.edit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object BackendConnection {
    private val client = OkHttpClient()
    private const val NGROKURL = BuildConfig.BACKEND_URL

    suspend fun sendIdTokenToBackendForGmailAccess(context: Context, idToken: String): Boolean {
        return try {
            val json = JSONObject().apply {
                put("id_token", idToken)
            }

            val requestBody = json.toString().toRequestBody("application/json".toMediaType())

            // Verificar si el idToken ya está autenticado
            val request = Request.Builder()
                .url("${NGROKURL}/users/auth/status")
                .post(requestBody)
                .build()

            val response = client.newCall(request).execute()
            val responseBody = response.body.string()

            val jsonResponse = JSONObject(responseBody)
            val authenticated = jsonResponse.getBoolean("authenticated")

            if (authenticated) {
                true
            } else {
                // Autenticar el idToken
                val request = Request.Builder()
                    .url("${NGROKURL}/users/auth/google")
                    .post(requestBody)
                    .build()

                val response = client.newCall(request).execute()
                val responseBody = response.body.string()

                if (!response.isSuccessful) {
                    Toast.makeText(context, responseBody, Toast.LENGTH_SHORT).show()
                    Log.e("Backend", "Error response: $responseBody")
                    return false
                }

                val jsonResponse = JSONObject(responseBody)
                val authUrl = jsonResponse.getString("auth_url")
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, authUrl, Toast.LENGTH_SHORT).show()
                }

                val prefs = context.getSharedPreferences("auth", Context.MODE_PRIVATE)
                prefs.edit { putBoolean("auth_complete", false) }
                val customTabsIntent = CustomTabsIntent.Builder().build()
                customTabsIntent.launchUrl(context, authUrl.toUri())

                while (true) {
                    val prefs = context.getSharedPreferences("auth", Context.MODE_PRIVATE)

                    val authenticated = prefs.getBoolean("auth_complete", false)

                    if (authenticated) break

                    Thread.sleep(500)
                }
                true
            }
        } catch (e: Exception) {
            Log.e("Backend", "Error enviando token", e)
            false
        }
    }
}