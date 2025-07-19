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

        // Asociar lógica al botón
        val recordExpensesButton = findViewById<Button>(R.id.recordExpenses)
        recordExpensesButton.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val credential = AuthController.getUserCredentials(this@MainActivity)

                    val (success, idToken) = AuthController.setupGmailAccess(this@MainActivity, credential)

                    if (success) {
                        GmailService.readMessages(idToken)
                    } else {
                        Log.e("Gmail", "Error")
                    }
                } catch (e: Exception) {
                    Log.e("Auth", "Error ejecutando flujo de autenticación", e)
                }
            }
        }
    }
}
