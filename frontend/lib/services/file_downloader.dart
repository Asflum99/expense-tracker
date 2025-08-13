import 'dart:io';
import 'dart:typed_data';
import 'package:expense_tracker/utils/result.dart';
import 'package:path_provider/path_provider.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:intl/intl.dart';
import 'package:media_store_plus/media_store_plus.dart';

class FileDownloader {
  Future<Result<String>> downloadToDevice(Uint8List csvContent) async {
    try {
      final fileName = _generateFileName();

      // Guardar archivo en ubicación temporal interna
      final tempDir = await getTemporaryDirectory();
      final tempFile = File('${tempDir.path}/$fileName');
      await tempFile.writeAsBytes(csvContent);

      // Guardar en carpeta pública Downloads usando MediaStore
      final saveInfo = await MediaStore().saveFile(
        tempFilePath: tempFile.path,
        dirType: DirType.download,
        dirName: DirName.download,
        relativePath: FilePath.root,
      );

      if (saveInfo != null) {
        return Result.success("Archivo guardado en Descargas");
      } else {
        return Result.failure(Exception("No se pudo guardar el archivo"));
      }
    } catch (e) {
      return Result.failure(Exception("Ocurrió un error inesperado: $e"));
    }
  }

  String _generateFileName() {
    final lima = tz.getLocation('America/Lima');
    final now = tz.TZDateTime.now(lima);
    final formatter = DateFormat('yyyy-MM-dd');
    final formattedDate = formatter.format(now);
    return 'Gastos_$formattedDate.csv';
  }
}
