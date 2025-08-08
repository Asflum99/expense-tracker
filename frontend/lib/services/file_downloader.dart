import 'package:expense_tracker/utils/result.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:intl/intl.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class FileDownloader {
  Future<Result<String>> downloadToDevice(String csvContent) async {
    try {
      final Directory? downloadsDir = await getDownloadsDirectory();
      final fileName = _generateFileName();

      if (downloadsDir == null) {
        return Result.failure(Exception("Carpeta de descargas no encontrada"));
      }

      final filePath = "${downloadsDir.path}/$fileName";
      final file = File(filePath);

      await file.writeAsString(csvContent);

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
