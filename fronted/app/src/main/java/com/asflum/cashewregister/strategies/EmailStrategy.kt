package com.asflum.cashewregister.strategies

import com.google.api.services.gmail.Gmail

interface EmailStrategy {
    suspend fun processMessages(
        gmailService: Gmail,
        after: Long,
        before: Long
    ): MutableList<MutableMap<String, Any>>
}