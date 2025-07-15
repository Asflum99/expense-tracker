package com.asflum.cashewregister

import android.content.Context
import androidx.core.content.edit

object UserPrefs {
    fun saveUserEmail(context: Context, email: String) {
        context.getSharedPreferences("user", Context.MODE_PRIVATE).edit {
            putString("userEmail", email)
        }
    }
    fun saveUserId(context: Context, userId: String) {
        context.getSharedPreferences("user", Context.MODE_PRIVATE).edit {
            putString("userId", userId)
        }
    }
}