package com.asflum.cashewregister

import android.content.ContentValues.TAG
import android.content.Context
import android.util.Log
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import okhttp3.OkHttpClient

object AuthController {
    private var userEmail: String = ""
    private val client = OkHttpClient()
    suspend fun handleRegisterClick(context: Context) {
        val credentialManager = CredentialProvider.getCredentialManager(context)
        val request = CredentialProvider.createCredentialRequest()

        try {
            val result = credentialManager.getCredential(
                request = request,
                context = context
            )
            handleSignIn(context, result)
            GmailService.continueWithGmailAccess(context, userEmail, client)
        } catch (e: GetCredentialException) {
            Log.e(TAG, "Error: ${e.message}")
        }
    }

    private suspend fun handleSignIn(context: Context, result: GetCredentialResponse) {
        // Handle the successfully returned credential
        when (val credential = result.credential) {

            // GoogleIdToken credential
            is CustomCredential -> {
                handleGoogleCredential(context, credential)
            }

            else -> {
                // Catch any unrecognized credential type here.
                Log.e(TAG, "Unexpected type of credential")
            }
        }
    }

    private suspend fun handleGoogleCredential(context: Context, credential: CustomCredential) {

        if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
            try {
                val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                val idToken = googleIdTokenCredential.idToken
                userEmail = googleIdTokenCredential.id
                UserPrefs.saveUserEmail(context, userEmail)
                BackendConnection.sendTokenToBackend(context, idToken, client)
            } catch (e: GoogleIdTokenParsingException) {
                Log.e(TAG, "ID Token invalid", e)
            }
        } else {
            Log.e(TAG, "CustomCredential no es un ID token de Google")
        }
    }
}