package com.asflum.cashewregister

import android.content.Context
import android.os.Environment
import android.widget.Toast
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone

object GmailService {
    private val client = OkHttpClient()
    private const val NGROKURL = BuildConfig.BACKEND_URL

    suspend fun readMessages(context: Context, idToken: String) {
        val json = JSONObject().apply {
            put("id_token", idToken)
        }

        val requestBody = json.toString().toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("${NGROKURL}/gmail/read-messages")
            .post(requestBody)
            .build()

        val response: Response

        withContext(Dispatchers.IO) {
            response = client.newCall(request).execute()
        }

        val jsonString = response.body.string()

        sendJSON(context, jsonString)
    }

    private suspend fun sendJSON(
        context: Context,
        movementsList: String
    ) {
        val requestBody = movementsList.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("${NGROKURL}/process-expenses")
            .post(requestBody)
            .build()

        val response: Response

        withContext(Dispatchers.IO) {
            response = client.newCall(request).execute()
        }

        if (!response.isSuccessful) {
            Toast.makeText(context, "Fallo al descargar el archivo", Toast.LENGTH_SHORT).show()
        } else {
            val inputStream = response.body.byteStream()
            val limaZone = TimeZone.getTimeZone("America/Lima")
            val today = Calendar.getInstance(limaZone)
            val formatter = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            formatter.timeZone = limaZone
            val formattedDate = formatter.format(today.time)
            val fileName = "Gastos_$formattedDate.csv"

            // Ruta a la carpeta Descargas
            val downloadsDir =
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
            val outputFile = File(downloadsDir, fileName)

            try {
                val outputStream = FileOutputStream(outputFile)
                inputStream.copyTo(outputStream)
                outputStream.close()
                inputStream.close()
                

                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Se descargó el archivo CSV", Toast.LENGTH_SHORT).show()
                }
            } catch (e: okio.IOException) {
                e.printStackTrace()
            }
        }
    }
}
