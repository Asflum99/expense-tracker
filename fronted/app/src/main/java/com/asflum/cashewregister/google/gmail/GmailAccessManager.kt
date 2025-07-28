package com.asflum.cashewregister.google.gmail

import android.content.Context
import com.asflum.cashewregister.google.auth.GmailBackendAuth
import com.asflum.cashewregister.google.auth.GoogleAuthHandler

object GmailAccessManager {

    suspend fun authenticateAndSetup(context: Context): Result<String> {
        val tokenResult = GoogleAuthHandler.getUserIdToken(context)
        if (tokenResult.isFailure) return tokenResult

        val backendResult = GmailBackendAuth.setupGmailAccess(context, tokenResult.toString())
        if (backendResult.isFailure) return backendResult

        return Result.success(tokenResult.toString())
    }
}