package com.asflum.cashewregister.strategies

import com.asflum.cashewregister.GmailService.accessMessage
import com.google.api.services.gmail.Gmail

class InterbankEmailStrategy : EmailStrategy {
    override suspend fun processMessages(
        gmailService: Gmail,
        after: Long,
        before: Long
    ): MutableList<MutableMap<String, Any>> {
        val query = "(from:servicioalcliente@netinterbank.com.pe) after:$after before:$before"

        val messagesResult = gmailService.users().messages().list("me")
            .setQ(query)
            .execute()

        val listToReturn = mutableListOf<MutableMap<String, Any>>()

        messagesResult?.messages?.forEach { message ->
            val messageBody = accessMessage(
                message.id
            )
            parseInterbankMessage(messageBody, listToReturn)
        }

        return listToReturn
    }

    private fun parseInterbankMessage(
        messageBody: String,
        listToReturn: MutableList<MutableMap<String, Any>>
    ) {

    }
}