package com.asflum.cashewregister.google.gmail

import android.content.Context
import android.net.Uri
import com.asflum.cashewregister.BackendProcessor
import com.asflum.cashewregister.FileDownloader

object GmailExpenseSyncManager {

    suspend fun syncAndDownloadExpenses(context: Context, idToken: String): Result<String> {
        val messagesResult = GmailService.readMessages(idToken)
        if (messagesResult.isFailure) return messagesResult

        val processResult = BackendProcessor.processExpenses(messagesResult.toString())
        if (processResult.isFailure) return processResult

        val downloadResult = FileDownloader.downloadToDevice(context, processResult.toString())
        if (downloadResult.isFailure) return downloadResult

        return downloadResult
    }
}