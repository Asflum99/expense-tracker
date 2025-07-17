package com.asflum.cashewregister

import android.content.Context
import androidx.credentials.GetCredentialRequest
import androidx.credentials.CredentialManager
import com.google.android.libraries.identity.googleid.GetGoogleIdOption

object CredentialProvider {
    const val WEB_CLIENT_ID = BuildConfig.WEB_CLIENT_ID
    fun getCredentialManager(context: Context): CredentialManager {
        return CredentialManager.create(context)
    }

    fun createCredentialRequest(): GetCredentialRequest {
        val googleIdOption = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setServerClientId(WEB_CLIENT_ID)
            .setRequestVerifiedPhoneNumber(false)
            .build()

        return GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()
    }
}

