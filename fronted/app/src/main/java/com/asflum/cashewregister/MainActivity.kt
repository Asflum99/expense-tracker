package com.asflum.cashewregister

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import android.widget.Button
import androidx.lifecycle.lifecycleScope
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.api.client.googleapis.extensions.android.gms.auth.GoogleAccountCredential
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Asociar lógica al botón
        val recordExpensesButton = findViewById<Button>(R.id.recordExpenses)
        recordExpensesButton.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val credential = AuthController.getUserCredentials(this@MainActivity)
                    // Primero verificar si hay credenciales válidas
                    if (credential != null) {
                        // Usuario autenticado, ahora configurar Gmail
                        if (AuthController.setupGmailAccess(this@MainActivity, credential)) {
                            // Listo para usar Gmail
                        } else {
                            // Error
                        }
                    } else {
                        // Solicitar autenticación
                        val result = AuthController.requestCredentials(this@MainActivity)
                        if (result != null) {
                            // Autenticación exitosa
                          //  navigateToExpenseRegistration()
                        } else {
                            // Manejar error de autenticación
                            Log.e("Auth", "Error")
                        }
                    }
                } catch (e: Exception) {
                    Log.e("Auth", "Error: ${e.message}")
                }
            }
        }
    }
}
