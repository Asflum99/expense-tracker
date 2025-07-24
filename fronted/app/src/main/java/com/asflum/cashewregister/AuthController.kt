package com.asflum.cashewregister

import android.content.Context
import android.widget.Toast
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
        val credentialManager = CredentialManager.create(context)

        val request = GetCredentialRequest.Builder()
            .addCredentialOption(getCredentialOptions())
            .build()

        return try {
            credentialManager.getCredential(context, request)
        } catch (e: GetCredentialException) {
            e.printStackTrace()
            null
        }
    }

    fun getCredentialOptions() : androidx.credentials.CredentialOption {
        return GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setAutoSelectEnabled(false)
            .setServerClientId(WEB_CLIENT_ID)
            .build()
    }

    suspend fun setupGmailAccess(
        context: Context,
        credential: GoogleIdTokenCredential
    ): Pair<Boolean, String> {
        return try {
            // 👇 Aquí revisas qué tipo de credencial se está recibiendo
            withContext(Dispatchers.Main) {
                val credType = credential.javaClass.name
                Toast.makeText(context, credType, Toast.LENGTH_LONG).show()
            }

            val idToken = credential.idToken

            var success = false

            withContext(Dispatchers.IO) {
                success = BackendConnection.sendIdTokenToBackendForGmailAccess(context, idToken)
            }

            Pair(success, idToken)
        } catch (e: Exception) {
            withContext(Dispatchers.Main) {
                Toast.makeText(context, "ERROR: ${e.message}", Toast.LENGTH_LONG).show()
            }
            Pair(false, "")
        }
    }
}
