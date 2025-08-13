import 'package:expense_tracker/utils/result.dart';
import 'package:expense_tracker/services/gmail_service.dart';
import 'package:expense_tracker/services/file_downloader.dart';

class GmailExpenseSyncManager {
  static Future<Result<String>> syncAndDownloadExpenses(
    String sessionToken,
  ) async {
    // Obtener los datos del backend (ya procesados con categorías)
    final messagesResult = await GmailService.readMessages(sessionToken);

    if (messagesResult.isFailure) {
      return Result.failure(messagesResult.exceptionOrNull()!);
    }

    final csvBytes = messagesResult.getOrNull()!;

    // Descargar el archivo CSV
    final downloadResult = await FileDownloader().downloadToDevice(csvBytes);

    return downloadResult;
  }
}
