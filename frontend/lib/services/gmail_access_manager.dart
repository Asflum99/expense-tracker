import 'package:expense_tracker/utils/result.dart';
import 'package:expense_tracker/services/google_auth_handler.dart';
import 'package:expense_tracker/services/gmail_backend.dart';

class GmailAccessManager {
  static Future<Result<String>> authenticateAndSetup() async {
    // Simulación del flujo de autenticación
    final tokenResult = await GoogleAuthHandler.getUserIdToken();

    if (tokenResult.isFailure) {
      return tokenResult;
    }

    final idToken = tokenResult.getOrNull()!;
    
    final backendResult = await GmailBackend().setupGmailAccess(idToken);
    if (backendResult.isFailure) {
      return backendResult;
    }

    return Result.success(idToken);
  }
}
