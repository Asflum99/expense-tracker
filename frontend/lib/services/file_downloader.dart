import 'package:downloadsfolder/downloadsfolder.dart';
import 'package:expense_tracker/utils/result.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:intl/intl.dart';
import 'dart:io';
import 'dart:typed_data';

class FileDownloader {
  Future<Result<String>> downloadToDevice(Uint8List csvContent) async {
    try {
      final fileName = _generateFileName();
      Directory downloadDirectory = await getDownloadDirectory();

      if (!await downloadDirectory.exists()) {
        return Result.failure(
          Exception("No se pudo acceder a la carpeta de descargas"),
        );
      }

      final filePath = "${downloadDirectory.path}/$fileName";
      final file = File(filePath);

      await file.writeAsBytes(csvContent);

      return Result.success("Archivo guardado en Descargas");
    } catch (e) {
      return Result.failure(Exception("Ocurrio un error inesperado: $e"));
    }
  }

  String _generateFileName() {
    final lima = tz.getLocation('America/Lima');
    final now = tz.TZDateTime.now(lima);

    final formatter = DateFormat('yyyy-MM-dd');
    final formattedDate = formatter.format(now);

    final fileName = 'Gastos_$formattedDate.csv';
    return fileName;
  }
}
