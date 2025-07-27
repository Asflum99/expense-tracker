package com.asflum.cashewregister

import android.content.Context
import android.os.Environment
import android.widget.Toast
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.ResponseBody
import okio.IOException
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone

object JsonDownloader {
    suspend fun downloadToDevice(context: Context, categorizedJson: ResponseBody) {
        val inputStream = categorizedJson.byteStream()
        val limaZone = TimeZone.getTimeZone("America/Lima")
        val today = Calendar.getInstance(limaZone)
        val formatter = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
        formatter.timeZone = limaZone
        val formattedDate = formatter.format(today.time)
        val fileName = "Gastos_$formattedDate.csv"

        // Ruta a la carpeta Descargas
        val downloadsDir =
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        val outputFile = File(downloadsDir, fileName)

        try {
            val outputStream = FileOutputStream(outputFile)
            inputStream.copyTo(outputStream)
            outputStream.close()
            inputStream.close()


            withContext(Dispatchers.Main) {
                Toast.makeText(context, "Se descargó el archivo CSV", Toast.LENGTH_SHORT).show()
            }
        } catch (e: IOException) {
            e.printStackTrace()
        }
    }
}