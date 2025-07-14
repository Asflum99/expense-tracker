package com.asflum.cashewregister

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.os.Environment
import android.util.Log
import android.widget.Button
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import android.util.Base64
import android.widget.Toast
import com.google.gson.Gson
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.FileOutputStream
import java.io.IOException
import java.io.File
import java.util.TimeZone
import androidx.credentials.GetCredentialRequest
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.GetCredentialException
import androidx.lifecycle.lifecycleScope
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import kotlinx.coroutines.launch
import androidx.core.content.edit
import com.google.api.client.googleapis.extensions.android.gms.auth.GoogleAccountCredential
import com.google.api.client.http.javanet.NetHttpTransport
import com.google.api.client.json.gson.GsonFactory
import com.google.api.services.gmail.Gmail
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext


class MainActivity : AppCompatActivity() {

    companion object {
        private val TAG = MainActivity::class.simpleName
    }

    private val gmailScope = listOf(
        "https://www.googleapis.com/auth/gmail.readonly"
    )

    private val webClientId = BuildConfig.WEB_CLIENT_ID

    private val client = OkHttpClient()
    private var gmailService: Gmail? = null
    private var userEmail: String = ""

    private val googleIdOption: GetGoogleIdOption = GetGoogleIdOption.Builder()
        .setFilterByAuthorizedAccounts(true)
        .setServerClientId(webClientId)
        .setAutoSelectEnabled(true)
        // TODO: Considerar el uso de nonce
        .build()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 1. Configurar Credential Manager
        val request: GetCredentialRequest = GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()
        val credentialManager = CredentialManager.create(this@MainActivity)

        // 2. Asociar lógica al botón
        val registerButton = findViewById<Button>(R.id.registerButton)
        registerButton.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val result = credentialManager.getCredential(
                        request = request,
                        context = this@MainActivity
                    )
                    handleSignIn(result)
                    continueWithGmailAccess()
                } catch (e: GetCredentialException) {
                    handleFailure(e)
                }
            }
        }
    }

    private fun handleSignIn(result: GetCredentialResponse) {
        // Handle the successfully returned credential
        when (val credential = result.credential) {

            // GoogleIdToken credential
            is CustomCredential -> {
                handleGoogleCredential(credential)
            }

            else -> {
                // Catch any unrecognized credential type here.
                Log.e(TAG, "Unexpected type of credential")
            }
        }
    }

    private fun handleGoogleCredential(credential: CustomCredential) {
        fun saveUserEmail(email: String) {
            getSharedPreferences("user", MODE_PRIVATE).edit {
                putString("userEmail", email)
            }
        }

        if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
            try {
                val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                val idToken = googleIdTokenCredential.idToken
                userEmail = googleIdTokenCredential.id
                saveUserEmail(userEmail)
                sendTokenToBackend(idToken)
            } catch (e: GoogleIdTokenParsingException) {
                Log.e(TAG, "ID Token invalid", e)
            }
        } else {
            Log.e(TAG, "CustomCredential no es un ID token de Google")
        }
    }

    private fun sendTokenToBackend(idToken: String) {
        fun saveUserId(userId: String) {
            getSharedPreferences("user", MODE_PRIVATE).edit {
                putString("userId", userId)
            }
        }

        val jsonString = """
            {
                "id_token": "$idToken"
            }
        """.trimIndent()

        val requestBody = jsonString.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("https://532dcd7bd4e0.ngrok-free.app/users/auth/google")
            .post(requestBody)
            .addHeader("ngrok-skip-browser-warning", "true")
            .build()

        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    client.newCall(request).execute().use { response ->
                        if (!response.isSuccessful) {
                            val errorBody = response.body.string()
                            Log.e(TAG, "Error response: $errorBody")
                            throw IOException("Unexpected code $response - Body: $errorBody")
                        }

                        val responseBody = response.body.string()
                        val json = JSONObject(responseBody)
                        val userId = json.getString("userid")

                        withContext(Dispatchers.Main) {
                            saveUserId(userId)
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Log.e(TAG, "Error enviando token al backend", e)
                    Toast.makeText(this@MainActivity, "Error de conexión", Toast.LENGTH_SHORT)
                        .show()
                }
            }
        }
    }

    private fun handleFailure(e: Exception) {
        Log.e(TAG, "Error during Google Sign In", e)

        Toast.makeText(this, "No se pudo iniciar sesión. Inténtalo de nuevo.", Toast.LENGTH_SHORT)
            .show()
    }

    // 3. Función para continuar si tiene acceso
    private fun continueWithGmailAccess() {
        fun getUserEmail(): String {
            // ✅ Usar la variable de clase si está disponible
            return userEmail.ifEmpty {
                // Fallback: obtener de SharedPreferences
                getSharedPreferences("user", MODE_PRIVATE).getString("userEmail", "") ?: ""
            }
        }

        fun initializeGmailService(credential: GoogleAccountCredential) {
            val transport = NetHttpTransport()
            val jsonFactory = GsonFactory.getDefaultInstance()

            gmailService = Gmail.Builder(transport, jsonFactory, credential)
                .setApplicationName("email reader")
                .build()
        }

        val credential = GoogleAccountCredential.usingOAuth2(
            this, gmailScope
        )

        // Configurar la cuenta (necesitas obtener el email del usuario)
        credential.selectedAccountName = getUserEmail()

        // Inicializar el servicio Gmail
        initializeGmailService(credential)

        // Usar el servicio de Gmail
        readGmailMessages()
    }

    private fun readGmailMessages() {
        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) {
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
                    sendJSON(client, movementsList)

                }
            } catch (e: Exception) {
                Log.e("GMAIL_API", "Error: ${e.message}")
            }
        }
    }

    suspend fun accessMessage(
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
                    // Caso simple: todo el cuerpo está en payload.body
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

    private fun sendJSON(
        client: OkHttpClient,
        movementsList: MutableList<MutableMap<String, Any>>
    ) {
        val gson = Gson()
        val jsonString = gson.toJson(movementsList)
        val requestBody = jsonString.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("https://532dcd7bd4e0.ngrok-free.app/process-expenses")
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Toast.makeText(
                        this@MainActivity,
                        "Falló al descargar el archivo",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }

            override fun onResponse(call: Call, response: Response) {
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

                    runOnUiThread {
                        Toast.makeText(
                            this@MainActivity,
                            "Se descargó el archivo CSV",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: IOException) {
                    e.printStackTrace()
                }
            }
        })
    }
}
