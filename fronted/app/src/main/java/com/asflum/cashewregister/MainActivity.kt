package com.asflum.cashewregister

import android.app.AlertDialog
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.google.android.gms.auth.api.signin.*
import com.google.android.gms.common.api.Scope
import com.google.android.gms.common.api.ApiException
import android.content.Intent
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
import java.util.Date

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
                val query = "(from:notificaciones@yape.pe OR from:notificaciones@notificacionesbcp.com.pe) after:$todayStr before:$tomorrowStr"
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
            readMessage(message)
        } else {
            Log.e("GMAIL_API", "Error ${response.code}: ${response.message}")
        }
    }
    fun readMessage(message: JSONObject) {
        val payload = message.getJSONObject("payload")
        val parts = payload.getJSONArray("parts")
        for (i in 0 until parts.length()) {
            val part = parts.getJSONObject(i)
            if (part.optString("mimeType") == "text/plain") {
                val data = part.optJSONObject("body")?.optString("data")
                if (!data.isNullOrEmpty()) {
                    val decoded = Base64.decode(data, Base64.URL_SAFE)
                    val body = String(decoded, Charsets.UTF_8)
                    val amountRegex = Regex("""\d+\.\d+""")
                    val dateRegex = Regex("""(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)""")
                    val beneficiaryRegex = Regex("""Nombre del Beneficiario\s+(.+)""")
                    val amount = amountRegex.find(body)?.value
                    val beneficiary = beneficiaryRegex.find(body)?.groups?.get(1)?.value

                    // Convertir fecha a formato requerido por Cashew
                    val dateDate = dateRegex.find(body)?.groups?.get(1)?.value ?: "Fecha desconocida"
                    val inputFormat = SimpleDateFormat("dd MMMM yyyy", Locale("es", "PE"))
                    val outputFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                    val parsedDate = inputFormat.parse(dateDate) ?: "Fecha desconocida"
                    val dateFormated = outputFormat.format(parsedDate)

                    // Convertir hora a formato requerido por Cashew
                    val dateTime = dateRegex.find(body)?.groups?.get(2)?.value ?: "Hora desconocida"
                    val inputTime = SimpleDateFormat("hh:mma", Locale("es", "PE"))
                    val originalTime = dateTime.replace(".", "").replace("a m", "AM").replace("p m", "PM")
                    val outputTime = SimpleDateFormat("hh:mm", Locale.getDefault())
                    val parsedTime = inputTime.parse(originalTime) ?: "Hora desconocida"
                    val timeFormated = outputTime.format(parsedTime)

                    Log.d("VALUES", "Monto: -${amount}. Fecha: ${dateFormated}. Hora: ${timeFormated}. Beneficiario: ${beneficiary}.")
                }
            }
        }
    }
}
