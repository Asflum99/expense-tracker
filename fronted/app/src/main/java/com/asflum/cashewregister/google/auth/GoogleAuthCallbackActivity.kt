package com.asflum.cashewregister.google.auth

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.localbroadcastmanager.content.LocalBroadcastManager

class GoogleAuthCallbackActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val intent = Intent("cashew.AUTH_COMPLETE")
        LocalBroadcastManager.getInstance(this).sendBroadcast(intent)
    }
}