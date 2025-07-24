package com.asflum.cashewregister

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import android.widget.Button
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import android.widget.Toast
import androidx.credentials.CustomCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Asociar lógica al botón
        val recordExpensesButton = findViewById<Button>(R.id.recordExpenses)
        recordExpensesButton.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val credential = AuthController.getUserCredentials(this@MainActivity)?.credential

                    var success = false
                    var idToken = ""

                    when (credential) {
                        is GoogleIdTokenCredential -> {
                            val result = AuthController.setupGmailAccess(this@MainActivity, credential)
                            success = result.first
                            idToken = result.second
                        }
                        is CustomCredential -> {
                            if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                                val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                                val result = AuthController.setupGmailAccess(this@MainActivity, googleIdTokenCredential)
                                success = result.first
                                idToken = result.second
                            }
                            else {
                                Toast.makeText(this@MainActivity, credential.type, Toast.LENGTH_SHORT).show()
                            }
                        }
                        else -> {
                            Toast.makeText(this@MainActivity, "ga", Toast.LENGTH_SHORT).show()
                        }
                    }

                    if (success) {
                        Toast.makeText(this@MainActivity, "🎯 Autenticación OK, leyendo mensajes...", Toast.LENGTH_SHORT).show()
                        GmailService.readMessages(this@MainActivity, idToken)
                    } else {
                        Toast.makeText(this@MainActivity, "❌ Falló la autenticación con Gmail", Toast.LENGTH_SHORT).show()
                        Log.e("Gmail", "Error")
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@MainActivity, "🔥 Error: ${e.message}", Toast.LENGTH_LONG).show()
                    e.printStackTrace()
                }
            }
        }
    }
}
