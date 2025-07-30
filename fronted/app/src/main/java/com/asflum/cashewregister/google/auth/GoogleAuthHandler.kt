package com.asflum.cashewregister.google.auth

import android.content.Context
import androidx.credentials.Credential
import androidx.credentials.CredentialManager
import androidx.credentials.CredentialOption
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import com.asflum.cashewregister.BuildConfig
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential

object GoogleAuthHandler {
    const val WEB_CLIENT_ID = BuildConfig.WEB_CLIENT_ID

    suspend fun getUserIdToken(context: Context): Result<String> {
        val credentialManager = CredentialManager.create(context)
        val request = GetCredentialRequest.Builder()
            .addCredentialOption(getCredentialOptions())
            .build()

        return try {
            val result = credentialManager.getCredential(context, request)
            val credential = result.credential

            val idToken = extractIdTokenFromCredential(credential)
            Result.success(idToken)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun getCredentialOptions(): CredentialOption {
        return GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setAutoSelectEnabled(false)
            .setServerClientId(WEB_CLIENT_ID)
            .build()
    }

    private fun extractIdTokenFromCredential(credential: Credential): String {
        return when (credential) {
            is GoogleIdTokenCredential -> credential.idToken

            is CustomCredential -> {
                if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                    val googleCred = GoogleIdTokenCredential.createFrom(credential.data)
                    googleCred.idToken
                } else {
                    throw UnsupportedOperationException("Tipo de credencial personalizada no soportada")
                }
            }

            else -> throw IllegalArgumentException("Tipo de credencial desconocida")
        }
    }
}