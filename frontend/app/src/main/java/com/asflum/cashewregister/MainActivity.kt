package com.asflum.cashewregister

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import android.widget.Button
import android.widget.Toast
import androidx.lifecycle.lifecycleScope
import com.asflum.cashewregister.google.gmail.GmailAccessManager
import com.asflum.cashewregister.google.gmail.GmailExpenseSyncManager
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
                    val tokenResult = GmailAccessManager.authenticateAndSetup(this@MainActivity)
                    if (tokenResult.isFailure) {
                        Toast.makeText(
                            this@MainActivity,
                            tokenResult.exceptionOrNull()?.message,
                            Toast.LENGTH_SHORT
                        ).show()
                        return@launch
                    }

                    val idToken = tokenResult.getOrNull()!!
                    val syncResult =
                        GmailExpenseSyncManager.syncAndDownloadExpenses(this@MainActivity, idToken)
                    if (syncResult.isFailure) {
                        Toast.makeText(
                            this@MainActivity,
                            syncResult.exceptionOrNull()?.message,
                            Toast.LENGTH_SHORT
                        ).show()
                        return@launch
                    }

                    Toast.makeText(
                        this@MainActivity,
                        syncResult.getOrNull(),
                        Toast.LENGTH_SHORT
                    ).show()
                } catch (e: Exception) {
                    Toast.makeText(
                        this@MainActivity,
                        "Error inesperado: ${e.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }
}
