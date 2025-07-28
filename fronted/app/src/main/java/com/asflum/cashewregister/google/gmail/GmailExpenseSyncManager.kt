package com.asflum.cashewregister.google.gmail

import android.content.Context
import com.asflum.cashewregister.BackendProcessor
import com.asflum.cashewregister.JsonDownloader

object GmailExpenseSyncManager {

    suspend fun syncAndDownloadExpenses(context: Context, idToken: String) {
        val rawJson = GmailService.readMessagesAsJson(idToken)

        val categorizedJson = BackendProcessor.categorizeExpenses(rawJson)

        JsonDownloader.downloadToDevice(context, categorizedJson)
    }
}