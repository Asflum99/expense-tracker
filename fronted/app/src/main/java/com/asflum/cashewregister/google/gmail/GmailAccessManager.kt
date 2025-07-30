package com.asflum.cashewregister.google.gmail

import android.content.Context
import com.asflum.cashewregister.google.auth.GmailBackendAuth
import com.asflum.cashewregister.google.auth.GoogleAuthHandler

object GmailAccessManager {

    suspend fun authenticateAndSetup(context: Context): Result<String> {
        val tokenResult = GoogleAuthHandler.getUserIdToken(context)
        if (tokenResult.isFailure) return tokenResult

        val idToken = tokenResult.getOrNull() ?: return Result.failure(Exception("No se pudo obtener el token del usuario."))

        val backendResult = GmailBackendAuth.setupGmailAccess(context, idToken)
        if (backendResult.isFailure) return backendResult

        return Result.success(idToken)
    }
}