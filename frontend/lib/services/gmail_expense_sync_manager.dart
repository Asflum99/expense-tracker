import 'package:expense_tracker/utils/result.dart';
import 'package:expense_tracker/services/gmail_service.dart';
import 'package:expense_tracker/services/file_downloader.dart';

class GmailExpenseSyncManager {
  static Future<Result<String>> syncAndDownloadExpenses(String sessionToken) async {
    final messagesResult = await GmailService.readMessages(sessionToken);

    if (messagesResult.isFailure) {
      return Result.failure(messagesResult.exceptionOrNull()!);
    }

    final messages = messagesResult.getOrNull()!;

    final downloadResult = await FileDownloader().downloadToDevice(messages);
    if (downloadResult.isFailure) {
      return Result.failure(downloadResult.exceptionOrNull()!);
    }

    return downloadResult;
  }
}