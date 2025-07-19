package com.asflum.cashewregister

import android.content.Context
import android.os.Environment
import android.util.Base64
import android.util.Log
import android.widget.Toast
import com.asflum.cashewregister.strategies.InterbankEmailStrategy
import com.asflum.cashewregister.strategies.YapeEmailStrategy
import com.google.api.client.googleapis.extensions.android.gms.auth.GoogleAccountCredential
import com.google.api.client.http.javanet.NetHttpTransport
import com.google.api.client.json.gson.GsonFactory
import com.google.api.services.gmail.Gmail
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
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
    private lateinit var gmailService: Gmail

    suspend fun readMessages(idToken: String) {
        val json = JSONObject().apply {
            put("id_token", idToken)
        }

        val requestBody = json.toString().toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("${NGROKURL}/gmail/read-messages")
            .post(requestBody)
            .build()

        withContext(Dispatchers.IO) {
            client.newCall(request).execute()
        }
    }

    private suspend fun readGmailMessages(
        context: Context
    ) {
        withContext(Dispatchers.IO) {
            try {
                // Establecer zona horario de Lima
                val limaZone = TimeZone.getTimeZone("America/Lima")

                // Armar fecha
                val today = Calendar.getInstance(limaZone).apply {
                    set(Calendar.HOUR_OF_DAY, 0)
                    set(Calendar.MINUTE, 0)
                    set(Calendar.SECOND, 0)
                    set(Calendar.MILLISECOND, 0)
                }
                val tomorrow = Calendar.getInstance(limaZone).apply {
                    time = today.time
                    add(Calendar.DATE, 1)
                }

                val after = today.timeInMillis / 1000
                val before = tomorrow.timeInMillis / 1000

                val strategies = listOf(
                    InterbankEmailStrategy(),
                    YapeEmailStrategy()
                )

                val movementsList = buildList {
                    for (strategy in strategies) {
                        addAll(strategy.processMessages(gmailService, after, before))
                    }
                }.toMutableList()

                sendJSON(context, movementsList)
            } catch (e: Exception) {
                Log.e("GMAIL_API", "Error: ${e.message}")
            }
        }
    }

    suspend fun accessMessage(
        messageId: String
    ): String {
        var messageBody = ""
        try {
            withContext(Dispatchers.IO) {
                val message =
                    gmailService.users().messages().get("me", messageId).setFormat("full")
                        .execute()

                val payload = message?.payload

                val bodyData = when {
                    // Caso simple: el cuerpo está en payload.body
                    payload?.body?.data != null -> payload.body.data

                    // Caso multipart: buscar parte con mimeType "text/plain" o "text/html"
                    payload?.parts != null -> {
                        payload.parts
                            .firstOrNull { it.mimeType == "text/plain" || it.mimeType == "text/html" }
                            ?.body
                            ?.data
                    }

                    else -> null
                }

                // Decodificar el cuerpo del mensaje (está en Base64 URL-safe)
                val decodedBytes = Base64.decode(bodyData, Base64.URL_SAFE)
                messageBody = String(decodedBytes, Charsets.UTF_8)
            }
        } catch (e: Exception) {
            Log.e("GmailAccess", "Error al acceder al mensaje", e)
            null
        }
        return messageBody
    }

    private suspend fun sendJSON(
        context: Context,
        movementsList: MutableList<MutableMap<String, Any>>
    ) {
        val gson = Gson()
        val jsonString = gson.toJson(movementsList)
        val requestBody = jsonString.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("${NGROKURL}/process-expenses")
            .post(requestBody)
            .build()

        val response = client.newCall(request).execute()

        if (!response.isSuccessful) {
            Toast.makeText(context, "Fallo al descargar el archivo", Toast.LENGTH_SHORT).show()
        } else {
            val inputStream = response.body.byteStream()
            val limaZone = TimeZone.getTimeZone("America/Lima")
            val today = Calendar.getInstance(limaZone)
            val formatter = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            formatter.timeZone = limaZone
            val formattedDate = formatter.format(today.time)
            val fileName = "test_gastos_$formattedDate.csv"

            // Ruta a la carpeta Descargas
            val downloadsDir =
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
            val outputFile = File(downloadsDir, fileName)

            try {
                val outputStream = FileOutputStream(outputFile)
                inputStream.copyTo(outputStream)
                outputStream.close()
                inputStream.close()

                Log.d("CSV", "Archivo guardado en: ${outputFile.absolutePath}")

                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Se descargó el archivo CSV", Toast.LENGTH_SHORT).show()
                }
            } catch (e: okio.IOException) {
                e.printStackTrace()
            }
        }
    }
}
