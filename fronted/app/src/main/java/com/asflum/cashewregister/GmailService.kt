package com.asflum.cashewregister

import android.content.Context
import android.os.Environment
import android.util.Base64
import android.util.Log
import android.widget.Toast
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
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone

object GmailService {
    private var gmailService: Gmail? = null
    private val gmailScope = listOf(
        "https://www.googleapis.com/auth/gmail.readonly"
    )

    suspend fun continueWithGmailAccess(context: Context, userEmail: String, client: OkHttpClient) {
        fun initializeGmailService(credential: GoogleAccountCredential) {
            val transport = NetHttpTransport()
            val jsonFactory = GsonFactory.getDefaultInstance()

            gmailService = Gmail.Builder(transport, jsonFactory, credential)
                .setApplicationName("email reader")
                .build()
        }

        val credential = GoogleAccountCredential.usingOAuth2(
            context, gmailScope
        )

        // Configurar la cuenta (necesitas obtener el email del usuario)
        credential.selectedAccountName = userEmail

        // Inicializar el servicio Gmail
        initializeGmailService(credential)

        // Usar el servicio de Gmail
        readGmailMessages(context, client)
    }

    private suspend fun readGmailMessages(context: Context, client: OkHttpClient) {
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

                val query = "(from:notificaciones@yape.pe) after:$after before:$before"

                val messagesResult = gmailService?.users()?.messages()?.list("me")
                    ?.setQ(query)
                    ?.execute()

                val movementsList: MutableList<MutableMap<String, Any>> = mutableListOf()

                messagesResult?.messages?.forEach { message ->
                    accessMessage(
                        message.id,
                        movementsList
                    )
                }

                sendJSON(context, client, movementsList)
            } catch (e: Exception) {
                Log.e("GMAIL_API", "Error: ${e.message}")
            }
        }
    }

    private suspend fun accessMessage(
        messageId: String,
        movementsList: MutableList<MutableMap<String, Any>>
    ) {
        try {
            withContext(Dispatchers.IO) {
                val dataToSend: MutableMap<String, Any> = mutableMapOf(
                    "date" to "",
                    "amount" to 0,
                    "category" to "",
                    "title" to "",
                    "note" to "",
                    "beneficiary" to "",
                    "account" to ""
                )

                val message =
                    gmailService?.users()?.messages()?.get("me", messageId)?.setFormat("full")
                        ?.execute()

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
                val messageBody = String(decodedBytes, Charsets.UTF_8)

                val amountRegex = Regex("""\d+\.\d+""")
                val dateRegex =
                    Regex("""(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)""")
                val beneficiaryRegex = Regex("""Nombre del Beneficiario\s+(.+)""")
                val amountStr = amountRegex.find(messageBody)?.value ?: "Monto desconocido"
                val amountFloat = amountStr.toFloatOrNull()?.let { -it } ?: 0
                val beneficiary = beneficiaryRegex.find(messageBody)?.groups?.get(1)?.value
                    ?: "Beneficiario desconocido"

                // Convertir fecha a formato requerido por Cashew
                val dateDate =
                    dateRegex.find(messageBody)?.groups?.get(1)?.value ?: "Fecha desconocida"
                val inputFormat =
                    SimpleDateFormat("dd MMMM yyyy", Locale.forLanguageTag("es-PE"))
                val outputFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                val parsedDate = inputFormat.parse(dateDate) ?: "Fecha desconocida"
                val dateFormated = outputFormat.format(parsedDate)

                // Convertir hora a formato requerido por Cashew
                val dateTime =
                    dateRegex.find(messageBody)?.groups?.get(2)?.value ?: "Hora desconocida"
                val originalTime =
                    dateTime.replace(".", "").replace("a m", "AM").replace("p m", "PM")
                val inputTime = SimpleDateFormat("hh:mm a", Locale.US)
                val outputTime = SimpleDateFormat("HH:mm", Locale.getDefault())
                val parsedTime = inputTime.parse(originalTime) ?: "Hora desconocida"
                val timeFormated = outputTime.format(parsedTime)

                dataToSend["date"] = "$dateFormated $timeFormated"
                dataToSend["amount"] = amountFloat
                dataToSend["beneficiary"] = beneficiary

                movementsList.add(dataToSend)
            }
        } catch (e: Exception) {
            Log.e("GmailAccess", "Error al acceder al mensaje", e)
        }
    }

    private suspend fun sendJSON(
        context: Context,
        client: OkHttpClient,
        movementsList: MutableList<MutableMap<String, Any>>
    ) {
        val gson = Gson()
        val jsonString = gson.toJson(movementsList)
        val requestBody = jsonString.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("https://41809ea7de49.ngrok-free.app/process-expenses")
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
