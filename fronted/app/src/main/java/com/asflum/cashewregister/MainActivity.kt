package com.asflum.cashewregister

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.google.android.gms.auth.api.signin.*
import com.google.android.gms.common.api.Scope
import com.google.android.gms.common.api.ApiException
import android.content.Intent
import android.os.Environment
import android.util.Log
import android.widget.Button
import com.google.android.gms.auth.GoogleAuthUtil
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.net.URLEncoder
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
import androidx.credentials.PasswordCredential
import androidx.credentials.PublicKeyCredential
import androidx.credentials.exceptions.GetCredentialException
import androidx.lifecycle.lifecycleScope
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import com.google.api.client.googleapis.auth.oauth2.GoogleIdToken
import com.google.api.client.googleapis.auth.oauth2.GoogleIdTokenVerifier
import com.google.gson.JsonObject
import kotlinx.coroutines.launch
import okhttp3.MediaType
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import androidx.core.content.edit


class MainActivity : AppCompatActivity() {

    companion object {
        private val TAG = MainActivity::class.simpleName
    }

    private val gmailScope = Scope("https://www.googleapis.com/auth/gmail.readonly")

    private val webClientId = BuildConfig.WEB_CLIENT_ID

    private val client = OkHttpClient()

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
        if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
            try {
                val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                val idToken = googleIdTokenCredential.idToken
                sendTokenToBackend(idToken)
            } catch (e: GoogleIdTokenParsingException) {
                Log.e(TAG, "ID Token invalid", e)
            }
        } else {
            Log.e(TAG, "CustomCredential no es un ID token de Google")
        }
    }

    private fun sendTokenToBackend(idToken: String) {
        val requestBody = """
            {
                "id_token": "$idToken"
            }
        """.trimIndent().toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("https://5e04-2001-1388-1760-9db6-82b2-6c7c-599a-1700.ngrok-free.app/users/auth/google")
            .post(requestBody)
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Unexpected code $response")

            val responseBody = response.body.string()
            val json = JSONObject(responseBody)
            val userId = json.getString("userid")
            saveUserId(userId)
            continueWithGmailAccess(userId)
        }
    }

    private fun saveUserId(userId: String) {
        getSharedPreferences("user", MODE_PRIVATE).edit {
            putString("userId", userId)
        }
    }

    private fun handleFailure(e: Exception) {
        Log.e(TAG, "Error during Google Sign In", e)

        Toast.makeText(this, "No se pudo iniciar sesión. Inténtalo de nuevo.", Toast.LENGTH_SHORT)
            .show()
    }

    // 3. Función para continuar si tiene acceso
    private fun continueWithGmailAccess(userId: String) {
        val googleAccount = account.account
        if (googleAccount == null) {
            Log.e("GMAIL_AUTH", "Cuenta de Google nula")
            return
        }

        val scope = "oauth2:https://www.googleapis.com/auth/gmail.readonly"
        Thread {
            try {
                val token = GoogleAuthUtil.getToken(this@MainActivity, googleAccount, scope)

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

                // Armar query y URL
                val query = "(from:notificaciones@yape.pe) after:$after before:$before"
                val encodedQuery = URLEncoder.encode(query, "UTF-8")
                val url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?q=$encodedQuery"

                // Hacer request con OkHttp
                val request = Request.Builder()
                    .url(url)
                    .addHeader("Authorization", "Bearer $token")
                    .build()

                val response = client.newCall(request).execute()

                if (response.isSuccessful) {
                    val body = response.body.string()
                    val message = JSONObject(body)
                    accessMessage(token, client, message)
                } else {
                    Log.e("GMAIL_API", "Error ${response.code}: ${response.message}")
                }
            } catch (e: Exception) {
                Log.e("GMAIL_API", "Excepción: ${e.message}")
            }
        }.start()
    }

    fun accessMessage(token: String, client: OkHttpClient, message: JSONObject) {
        // Extraer todos los correos del día
        val messages = message.optJSONArray("messages")

        // Iterar sobre cada correo
        if (messages != null) {
            val movementsList: MutableList<MutableMap<String, String>> = mutableListOf()
            for (i in 0 until messages.length()) {
                val messageItem = messages.getJSONObject(i)
                val messageId = messageItem.getString("id")

                // Armar url
                val url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/$messageId"

                // Hacer request
                val request = Request.Builder()
                    .url(url)
                    .addHeader("Authorization", "Bearer $token")
                    .build()

                val response = client.newCall(request).execute()

                if (response.isSuccessful) {
                    val body = response.body.string()
                    val message = JSONObject(body)
                    movementsList.add(readMessage(message))
                } else {
                    Log.e("GMAIL_API", "Error ${response.code}: ${response.message}")
                }
            }
            sendJSON(client, movementsList)
        }
    }

    fun readMessage(message: JSONObject): MutableMap<String, String> {
        val payload = message.getJSONObject("payload")
        val parts = payload.getJSONArray("parts")
        val dataToSend = mutableMapOf<String, String>(
            "date" to "",
            "amount" to "",
            "category" to "",
            "title" to "",
            "note" to "",
            "beneficiary" to "",
            "account" to ""
        )
        for (i in 0 until parts.length()) {
            val part = parts.getJSONObject(i)
            if (part.optString("mimeType") == "text/plain") {
                val data = part.optJSONObject("body")?.optString("data")
                if (!data.isNullOrEmpty()) {
                    val decoded = Base64.decode(data, Base64.URL_SAFE)
                    val body = String(decoded, Charsets.UTF_8)
                    val amountRegex = Regex("""\d+\.\d+""")
                    val dateRegex =
                        Regex("""(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)""")
                    val beneficiaryRegex = Regex("""Nombre del Beneficiario\s+(.+)""")
                    val amount = amountRegex.find(body)?.value ?: "Monto desconocido"
                    val beneficiary = beneficiaryRegex.find(body)?.groups?.get(1)?.value
                        ?: "Beneficiario desconocido"

                    // Convertir fecha a formato requerido por Cashew
                    val dateDate =
                        dateRegex.find(body)?.groups?.get(1)?.value ?: "Fecha desconocida"
                    val inputFormat = SimpleDateFormat("dd MMMM yyyy", Locale("es", "PE"))
                    val outputFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                    val parsedDate = inputFormat.parse(dateDate) ?: "Fecha desconocida"
                    val dateFormated = outputFormat.format(parsedDate)

                    // Convertir hora a formato requerido por Cashew
                    val dateTime = dateRegex.find(body)?.groups?.get(2)?.value ?: "Hora desconocida"
                    val originalTime =
                        dateTime.replace(".", "").replace("a m", "AM").replace("p m", "PM")
                    val inputTime = SimpleDateFormat("hh:mm a", Locale.US)
                    val outputTime = SimpleDateFormat("HH:mm", Locale.getDefault())
                    val parsedTime = inputTime.parse(originalTime) ?: "Hora desconocida"
                    val timeFormated = outputTime.format(parsedTime)

                    dataToSend["date"] = "$dateFormated $timeFormated"
                    dataToSend["amount"] = "-$amount"
                    dataToSend["beneficiary"] = beneficiary
                }
            }
        }
        return dataToSend
    }

    fun sendJSON(client: OkHttpClient, movementsList: MutableList<MutableMap<String, String>>) {
        val gson = Gson()
        val jsonString = gson.toJson(movementsList)
        val requestBody = jsonString.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("https://5e04-2001-1388-1760-9db6-82b2-6c7c-599a-1700.ngrok-free.app/process-expenses")
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
