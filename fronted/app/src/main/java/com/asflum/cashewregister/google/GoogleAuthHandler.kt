package com.asflum.cashewregister.google

import android.content.Context
import androidx.credentials.Credential
import androidx.credentials.CredentialManager
import androidx.credentials.CredentialOption
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import com.asflum.cashewregister.BuildConfig
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential

object GoogleAuthHandler {
    data class AuthTokenResult(val idToken: String?, val error: String? = null) {
        val isSuccess: Boolean get() = idToken != null && error == null
    }
    const val WEB_CLIENT_ID = BuildConfig.WEB_CLIENT_ID

    suspend fun getUserIdToken(context: Context): AuthTokenResult {

        // Empezamos obteniendo las credenciales del usuario
        val credentialManager = CredentialManager.Companion.create(context)
        val request = GetCredentialRequest.Builder()
            .addCredentialOption(getCredentialOptions())
            .build()

        return try {
            val result = credentialManager.getCredential(context, request)
            val credential = result.credential

            // Con la credencial ya obtenida, ahora podemos extraer el idToken
            extractIdTokenFromCredential(credential)

        } catch (e: GetCredentialException) {
            e.printStackTrace()
            AuthTokenResult(null, "Error al obtener las credenciales")
        }
    }

    private fun getCredentialOptions(): CredentialOption {
        return GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setAutoSelectEnabled(false)
            .setServerClientId(WEB_CLIENT_ID)
            .build()
    }

    private fun extractIdTokenFromCredential(credential: Credential): AuthTokenResult {
        return when (credential) {
            // Manejo de las credenciales de Google
            is GoogleIdTokenCredential -> {
                AuthTokenResult(credential.idToken, null)
            }

            // Manejo de las credenciales personalizadas
            is CustomCredential -> {

                // Manejo de la credencial personalizada que es del tipo GoogleIdTokenCredential
                if (credential.type == GoogleIdTokenCredential.Companion.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                    val googleIdTokenCredential = GoogleIdTokenCredential.Companion.createFrom(credential.data)
                    AuthTokenResult(googleIdTokenCredential.idToken, null)

                // Manejo de las credenciales personalizadas desconocidas (TODO)
                } else {
                    AuthTokenResult(null, "Tipo de credencial personalizada no soportada")
                }
            }

            // Manejo de credenciales desconocidas (TODO)
            else -> {
                AuthTokenResult(null, "Tipo de credencial desconocida")
            }
        }
    }
}