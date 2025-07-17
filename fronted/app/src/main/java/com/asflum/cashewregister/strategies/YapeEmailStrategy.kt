package com.asflum.cashewregister.strategies

import android.icu.text.SimpleDateFormat
import com.asflum.cashewregister.GmailService.accessMessage
import com.google.api.services.gmail.Gmail
import java.util.Locale

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
            val messageBody = accessMessage(
                message.id
            )
            parseYapeMessage(messageBody, listToReturn)
        }

        return listToReturn
    }

    private fun parseYapeMessage(
        messageBody: String,
        listToReturn: MutableList<MutableMap<String, Any>>
    ) {
        val dataToSend = mutableMapOf<String, Any>(
            "date" to "",
            "amount" to 0,
            "category" to "",
            "title" to "",
            "note" to "",
            "beneficiary" to "",
            "account" to ""
        )

        val amountRegex = Regex("""\d+\.\d+""")
        val dateRegex =
            Regex("""(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)""")
        val beneficiaryRegex = Regex("""Nombre del Beneficiario\s+(.+)""")
        val amountStr = amountRegex.find(messageBody)?.value ?: "Monto desconocido"
        val amountFloat = amountStr.toFloatOrNull()?.let { -it } ?: 0
        val beneficiary = beneficiaryRegex.find(messageBody)?.groups?.get(1)?.value
            ?: "Beneficiario desconocido"

        // Convertir fecha a formato requerido por Cashew
        val dateDate =
            dateRegex.find(messageBody)?.groups?.get(1)?.value ?: "Fecha desconocida"
        val inputFormat =
            SimpleDateFormat("dd MMMM yyyy", Locale.forLanguageTag("es-PE"))
        val outputFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
        val parsedDate = inputFormat.parse(dateDate) ?: "Fecha desconocida"
        val dateFormated = outputFormat.format(parsedDate)

        // Convertir hora a formato requerido por Cashew
        val dateTime =
            dateRegex.find(messageBody)?.groups?.get(2)?.value ?: "Hora desconocida"
        val originalTime =
            dateTime.replace(".", "").replace("a m", "AM").replace("p m", "PM")
        val inputTime = SimpleDateFormat("hh:mm a", Locale.US)
        val outputTime = SimpleDateFormat("HH:mm", Locale.getDefault())
        val parsedTime = inputTime.parse(originalTime) ?: "Hora desconocida"
        val timeFormated = outputTime.format(parsedTime)

        dataToSend["date"] = "$dateFormated $timeFormated"
        dataToSend["amount"] = amountFloat
        dataToSend["beneficiary"] = beneficiary

        listToReturn.add(dataToSend)
    }
}