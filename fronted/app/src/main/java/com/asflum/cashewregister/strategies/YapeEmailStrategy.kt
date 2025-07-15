package com.asflum.cashewregister.strategies

import com.asflum.cashewregister.GmailService.accessMessage
import com.google.api.services.gmail.Gmail

class YapeEmailStrategy : EmailStrategy {
    override suspend fun processMessages(
        gmailService: Gmail,
        after: Long,
        before: Long
    ): MutableList<MutableMap<String, Any>> {
        val query = "(from:notificaciones@yape.pe) after:$after before:$before"

        val messagesResult = gmailService.users().messages().list("me")
            .setQ(query)
            .execute()

        val listToReturn = mutableListOf<MutableMap<String, Any>>()

        messagesResult?.messages?.forEach { message ->
            accessMessage(
                message.id,
                listToReturn
            )
        }

        return listToReturn
    }
}