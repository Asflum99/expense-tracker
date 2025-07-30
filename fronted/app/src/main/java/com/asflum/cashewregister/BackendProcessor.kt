package com.asflum.cashewregister

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okio.IOException

object BackendProcessor {

    private const val API_URL = BuildConfig.API_URL
    private val client = OkHttpClient()

    suspend fun processExpenses(rawExpenses: String): Result<String> {
        return try {
            val requestBody = rawExpenses.toRequestBody("application/json".toMediaType())

            val request = Request.Builder()
                .url("${API_URL}/process-expenses")
                .post(requestBody)
                .build()

            val response: Response = withContext(Dispatchers.IO) {
                client.newCall(request).execute()
            }

            Result.success(response.body.toString())
        } catch (_: IOException) {
            Result.failure(Exception("Error de red. Revise su conexión e intente de nuevo."))
        } catch (e: Exception) {
            Result.failure(Exception("Error inesperado: ${e.localizedMessage}"))
        }
    }
}