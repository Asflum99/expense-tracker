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
import java.io.IOException

object GmailService {
    private val client = OkHttpClient()
    private const val API_URL = BuildConfig.API_URL

    suspend fun readMessages(idToken: String): Result<String> {
        return try {
            val json = JSONObject().apply {
                put("id_token", idToken)
            }

            val requestBody = json.toString().toRequestBody("application/json".toMediaType())

            val request = Request.Builder()
                .url("${API_URL}/gmail/read-messages")
                .post(requestBody)
                .build()

            val response: Response = withContext(Dispatchers.IO) {
                client.newCall(request).execute()
            }

            if (response.isSuccessful) {
                Result.success(response.body.string())
            } else {
                Result.failure(Exception("Error del servidor: ${response.code}"))
            }
        } catch (_: IOException) {
            Result.failure(Exception("Error de red. Revise su conexión e intente de nuevo."))
        } catch (e: Exception) {
            Result.failure(Exception("Error inesperado: ${e.localizedMessage}"))
        }
    }
}