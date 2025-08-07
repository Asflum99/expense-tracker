import 'package:expense_tracker/utils/result.dart';
import 'package:expense_tracker/services/gmail_service.dart';
import 'package:expense_tracker/services/backend_processor.dart';
import 'package:expense_tracker/services/file_downloader.dart';
import 'dart:convert';

class GmailExpenseSyncManager {
  static Future<Result<String>> syncAndDownloadExpenses(String sessionToken) async {
    final messagesResult = await GmailService.readMessages(sessionToken);

    if (messagesResult.isFailure) {
      return Result.failure(messagesResult.exceptionOrNull()!);
    }

    final messages = messagesResult.getOrNull()!;
    final dynamic lista = jsonDecode(messages);
    final List<Map<String, dynamic>> listaFinal = List<Map<String, dynamic>>.from(lista);

    final processResult = await BackendProcessor().processMessages(listaFinal);
    if (processResult.isFailure) {
      return Result.failure(processResult.exceptionOrNull()!);
    }

    final messagesProcessed = processResult.getOrNull()!;

    final downloadResult = await FileDownloader().downloadToDevice(messagesProcessed);
    if (downloadResult.isFailure) {
      return Result.failure(downloadResult.exceptionOrNull()!);
    }

    return downloadResult;
  }
}