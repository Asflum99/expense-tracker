package com.asflum.cashewregister

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import android.widget.Button
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Configurar Credential Manager
        val credentialManager = CredentialProvider.getCredentialManager(this@MainActivity)
        val request = CredentialProvider.createCredentialRequest()

        // Asociar lógica al botón
        val recordExpensesButton = findViewById<Button>(R.id.recordExpenses)
        recordExpensesButton.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val result = credentialManager.getCredential(this@MainActivity, request)

                    AuthController.handleRegisterClick(this@MainActivity, result)
                } catch (e: Exception) {
                    Log.e("Auth", "Error: ${e.message}")
                }
            }
        }
    }
}
