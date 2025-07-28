package com.asflum.cashewregister.google.gmail

import com.asflum.cashewregister.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONObject

object GmailService {
    private val client = OkHttpClient()
    private const val API_URL = BuildConfig.API_URL

    suspend fun readMessagesAsJson(idToken: String): JSONObject {
        val json = JSONObject().apply {
            put("id_token", idToken)
        }

        val requestBody = json.toString().toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("${API_URL}/gmail/read-messages")
            .post(requestBody)
            .build()

        val response: Response

        withContext(Dispatchers.IO) {
            response = client.newCall(request).execute()
        }

        val responseBody = response.body.string()

        return JSONObject(responseBody)
    }
}