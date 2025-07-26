package com.asflum.cashewregister

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Button
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.asflum.cashewregister.google.GmailBackendAuth
import com.asflum.cashewregister.google.GmailService
import com.asflum.cashewregister.google.GoogleAuthHandler
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Asociar lógica al botón
        val recordExpensesButton = findViewById<Button>(R.id.recordExpenses)
        recordExpensesButton.setOnClickListener {
            lifecycleScope.launch {
                val result = GoogleAuthHandler.getUserIdToken(this@MainActivity)

                if (!result.isSuccess) {
                    // Manejar el caso de error
                    Toast.makeText(this@MainActivity, result.error, Toast.LENGTH_SHORT).show()
                    return@launch
                }

                val success = GmailBackendAuth.setupGmailAccess(this@MainActivity, result.idToken!!)

                if (!success) {
                    // Manejar el caso de error
                    return@launch
                }

                GmailService.readMessages(this@MainActivity, result.idToken)
            }
        }
    }
}
