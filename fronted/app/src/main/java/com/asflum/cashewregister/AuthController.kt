package com.asflum.cashewregister

import android.content.Context
import android.util.Log
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object AuthController {
    const val WEB_CLIENT_ID = BuildConfig.WEB_CLIENT_ID

    suspend fun getUserCredentials(context: Context): GetCredentialResponse? {
        return try {
            val credentialManager = CredentialManager.create(context)
            val request = GetCredentialRequest.Builder()
                .addCredentialOption(
                    GetGoogleIdOption.Builder()
                        .setFilterByAuthorizedAccounts(false)
                        .setServerClientId(WEB_CLIENT_ID)
                        .build()
                )
                .build()

            credentialManager.getCredential(context, request)
        } catch (e: GetCredentialException) {
            Log.e("Auth", "Error getting credentials: ${e.message}")
            null
        }
    }

    suspend fun setupGmailAccess(
        context: Context,
        credentialResponse: GetCredentialResponse?
    ): Pair<Boolean, String> {
        return try {
            val googleIdTokenCredential = credentialResponse?.credential as GoogleIdTokenCredential

            val idToken = googleIdTokenCredential.idToken

            var success = false

            withContext(Dispatchers.IO) {
                success = BackendConnection.sendIdTokenToBackendForGmailAccess(context, idToken)
            }

            Pair(success, idToken)
        } catch (e: Exception) {
            Log.e("Gmail", "Error setting up Gmail: ${e.message}")
            Pair(false, "")
        }
    }
}
