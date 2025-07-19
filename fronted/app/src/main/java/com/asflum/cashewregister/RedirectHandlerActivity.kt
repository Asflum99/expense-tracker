package com.asflum.cashewregister

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.edit

class RedirectHandlerActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Se cambiar el valor del archivo auth
        val prefs = getSharedPreferences("auth", MODE_PRIVATE)
        prefs.edit { putBoolean("auth_complete", true) }

        // Luego finalizas esta Activity para regresar al flujo principal
        finish()
    }
}