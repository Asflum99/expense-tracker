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

@Suppress("DEPRECATION")
class MainActivity : AppCompatActivity() {

    private val rcSignIn = 1000
    private val gmailScope = Scope("https://www.googleapis.com/auth/gmail.readonly")
    private lateinit var googleSignInClient: GoogleSignInClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 1. Configurar GoogleSignIn
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestEmail()
            .requestScopes(gmailScope)
            .build()

        googleSignInClient = GoogleSignIn.getClient(this, gso)

        // 2. Asociar lógica al botón
        val registerButton = findViewById<Button>(R.id.registerButton)
        registerButton.setOnClickListener {
            val account = GoogleSignIn.getLastSignedInAccount(this)

            if (account != null && GoogleSignIn.hasPermissions(account, gmailScope)) {
                continueWithGmailAccess(account)
            } else {
                val signInIntent = googleSignInClient.signInIntent
                startActivityForResult(signInIntent, rcSignIn)
            }
        }
    }

    // 3. Procesar el resultado del login
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == rcSignIn) {
            val task = GoogleSignIn.getSignedInAccountFromIntent(data)

            try {
                val account = task.getResult(ApiException::class.java)

                if (account != null && GoogleSignIn.hasPermissions(account, gmailScope)) {
                    continueWithGmailAccess(account)
                }
            } catch (e: ApiException) {
                Log.e("GMAIL_AUTH", "Sign-in failed: ${e.statusCode} - ${e.message}")
            }
        }
    }

    // 4. Función para continuar si tiene acceso
    private fun continueWithGmailAccess(account: GoogleSignInAccount) {
        val googleAccount = account.account
        if (googleAccount == null) {
            Log.e("GMAIL_AUTH", "Cuenta de Google nula")
            return
        }

        val scope = "oauth2:https://www.googleapis.com/auth/gmail.readonly"
        Thread {
            try {
                val token = GoogleAuthUtil.getToken(this@MainActivity, googleAccount, scope)

                // Armar fecha
                val formatter = SimpleDateFormat("yyyy/MM/dd", Locale.getDefault())
                val today = Calendar.getInstance()
                val tomorrow = Calendar.getInstance().apply { add(Calendar.DATE, 1) }

                val todayStr = formatter.format(today.time)
                val tomorrowStr = formatter.format(tomorrow.time)

                // Armar query y URL
                val query = "(from:notificaciones@yape.pe) after:$todayStr before:$tomorrowStr"
                val encodedQuery = URLEncoder.encode(query, "UTF-8")
                val url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?q=$encodedQuery"

                // Hacer request con OkHttp
                val client = OkHttpClient()
                val request = Request.Builder()
                    .url(url)
                    .addHeader("Authorization", "Bearer $token")
                    .build()

                val response = client.newCall(request).execute()

                if (response.isSuccessful) {
                    val body = response.body?.string()
                    val message = JSONObject(body ?: "")
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
        // Extrar id del mensaje
        val messages = message.optJSONArray("messages")
        val messageItem = messages?.getJSONObject(0)
        val messageId = messageItem?.getString("id")
        // Armar url
        val url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/$messageId"
        // Hacer request
        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $token")
            .build()

        val response = client.newCall(request).execute()

        if (response.isSuccessful) {
            val body = response.body?.string()
            val message = JSONObject(body ?: "")
            val movementsList = readMessage(message)
            sendJSON(client, movementsList)
        } else {
            Log.e("GMAIL_API", "Error ${response.code}: ${response.message}")
        }
    }
    fun readMessage(message: JSONObject): MutableList<MutableMap<String, String>> {
        val payload = message.getJSONObject("payload")
        val parts = payload.getJSONArray("parts")
        val dataToSend = mutableListOf<MutableMap<String, String>>()
        for (i in 0 until parts.length()) {
            val dictCreated = mutableMapOf<String, String>(
                "date" to "",
                "amount" to "",
                "category" to "",
                "title" to "",
                "note" to "",
                "beneficiary" to "",
                "account" to ""
            )
            val part = parts.getJSONObject(i)
            if (part.optString("mimeType") == "text/plain") {
                val data = part.optJSONObject("body")?.optString("data")
                if (!data.isNullOrEmpty()) {
                    val decoded = Base64.decode(data, Base64.URL_SAFE)
                    val body = String(decoded, Charsets.UTF_8)
                    val amountRegex = Regex("""\d+\.\d+""")
                    val dateRegex = Regex("""(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)""")
                    val beneficiaryRegex = Regex("""Nombre del Beneficiario\s+(.+)""")
                    val amount = amountRegex.find(body)?.value ?: "Monto desconocido"
                    val beneficiary = beneficiaryRegex.find(body)?.groups?.get(1)?.value ?: "Beneficiario desconocido"

                    // Convertir fecha a formato requerido por Cashew
                    val dateDate = dateRegex.find(body)?.groups?.get(1)?.value ?: "Fecha desconocida"
                    val inputFormat = SimpleDateFormat("dd MMMM yyyy", Locale("es", "PE"))
                    val outputFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                    val parsedDate = inputFormat.parse(dateDate) ?: "Fecha desconocida"
                    val dateFormated = outputFormat.format(parsedDate)

                    // Convertir hora a formato requerido por Cashew
                    val dateTime = dateRegex.find(body)?.groups?.get(2)?.value ?: "Hora desconocida"
                    val originalTime = dateTime.replace(".", "").replace("a m", "AM").replace("p m", "PM")
                    val inputTime = SimpleDateFormat("hh:mm a", Locale.US)
                    val outputTime = SimpleDateFormat("hh:mm", Locale.getDefault())
                    val parsedTime = inputTime.parse(originalTime) ?: "Hora desconocida"
                    val timeFormated = outputTime.format(parsedTime)

                    dictCreated["date"] = "$dateFormated $timeFormated"
                    dictCreated["amount"] = "-$amount"
                    dictCreated["beneficiary"] = beneficiary

                    dataToSend.add(dictCreated)
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
            .url("https://5810-2001-1388-1760-9db6-2a18-8168-7dc7-3d8b.ngrok-free.app/process-expenses")
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    Toast.makeText(this@MainActivity, "Falló al descargar el archivo", Toast.LENGTH_SHORT).show()
                }
            }
            override fun onResponse(call: Call, response: Response) {
                val inputStream = response.body?.byteStream() ?: return
                val fileName = "test_gastos1.csv"

                // Ruta a la carpeta Descargas
                val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                val outputFile = File(downloadsDir, fileName)

                try {
                    val outputStream = FileOutputStream(outputFile)
                    inputStream.copyTo(outputStream)
                    outputStream.close()
                    inputStream.close()

                    Log.d("CSV", "Archivo guardado en: ${outputFile.absolutePath}")

                    runOnUiThread {
                        Toast.makeText(this@MainActivity, "Se descargó el archivo CSV", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: IOException) {
                    e.printStackTrace()
                }
            }
        })
    }
}
