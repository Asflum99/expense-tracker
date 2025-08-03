package com.asflum.cashewregister.google.gmail

import android.content.Context
import com.asflum.cashewregister.BackendProcessor
import com.asflum.cashewregister.FileDownloader

object GmailExpenseSyncManager {

    suspend fun syncAndDownloadExpenses(context: Context, idToken: String): Result<String> {
        val messagesResult = GmailService.readMessages(idToken)
        if (messagesResult.isFailure) return messagesResult

        val messages = messagesResult.getOrNull() ?: return Result.failure(Exception("TODO"))

        val processResult = BackendProcessor.processExpenses(messages)
        if (processResult.isFailure) return processResult

        val messagesProcessed = processResult.getOrNull() ?: return Result.failure(Exception("TODO"))

        val downloadResult = FileDownloader.downloadToDevice(context, messagesProcessed)
        if (downloadResult.isFailure) return downloadResult

        return downloadResult
    }
}