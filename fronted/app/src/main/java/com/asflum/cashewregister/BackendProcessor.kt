package com.asflum.cashewregister

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.ResponseBody
import org.json.JSONObject

object BackendProcessor {

    private const val API_URL = BuildConfig.API_URL
    private val client = OkHttpClient()

    suspend fun categorizeExpenses(rawJson: JSONObject): ResponseBody {
        val requestBody = rawJson.toString().toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("${API_URL}/process-expenses")
            .post(requestBody)
            .build()

        val response: Response

        withContext(Dispatchers.IO) {
            response = client.newCall(request).execute()
        }

        return response.body
    }
}