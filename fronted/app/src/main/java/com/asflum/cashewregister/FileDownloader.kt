package com.asflum.cashewregister

import android.content.ContentValues
import android.content.Context
import android.provider.MediaStore
import okio.FileNotFoundException
import okio.IOException
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone

object FileDownloader {
    fun downloadToDevice(context: Context, csvContent: String): Result<String> {
        return try {
            // Formatear hora
            val limaZone = TimeZone.getTimeZone("America/Lima")
            val today = Calendar.getInstance(limaZone)
            val formatter = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            formatter.timeZone = limaZone
            val formattedDate = formatter.format(today.time)
            val fileName = "Gastos_$formattedDate.csv"

            val contentValues = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, "$fileName.csv")
                put(MediaStore.Downloads.MIME_TYPE, "text/csv")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }

            val contentResolver = context.contentResolver
            val collection = MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
            val uri = contentResolver.insert(collection, contentValues)

            if (uri != null) {
                contentResolver.openOutputStream(uri)?.use { outputStream ->
                    outputStream.write(csvContent.toByteArray())
                    outputStream.flush()
                }

                // Marcar como ya no pendiente
                contentValues.clear()
                contentValues.put(MediaStore.Downloads.IS_PENDING, 0)
                contentResolver.update(uri, contentValues, null, null)

                Result.success("Ya se descargó el archivo csv en la carpeta Descargas.")
            } else {
                Result.failure(Exception("No se pudo crear el archivo csv."))
            }
        } catch (_: FileNotFoundException) {
            Result.failure(Exception("Error al crear el archivo csv."))
        } catch (_: IOException) {
            Result.failure(Exception("Error durante la creación del archivo csv. Intente de nuevo."))
        }
    }
}