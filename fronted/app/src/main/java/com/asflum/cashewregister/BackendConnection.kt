package com.asflum.cashewregister

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

object BackendConnection {
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
}