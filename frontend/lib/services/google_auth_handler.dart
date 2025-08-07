import 'dart:async';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:expense_tracker/utils/result.dart';
import 'package:expense_tracker/services/gmail_backend.dart';

class GoogleAuthHandler {
  static Future<Result<String>> authenticationAndSetupAccess() async {
    try {
      final String serverClientId = const String.fromEnvironment(
        'WEB_CLIENT_ID',
      );
      final GoogleSignIn signIn = GoogleSignIn.instance;
      await signIn.initialize(serverClientId: serverClientId);

      final GoogleSignInAccount user = await signIn.authenticate(
        scopeHint: ['https://www.googleapis.com/auth/gmail.readonly'],
      );

      final idToken = user.authentication.idToken;

      if (idToken == null) {
        return Result.failure(Exception("No hay token"));
      }

      final backendResult = await GmailBackend().authenticateUserComplete(
        idToken,
      );

      if (backendResult.isFailure) {
        return Result.failure(backendResult.exceptionOrNull()!);
      }

      return backendResult;
    } catch (e) {
      return Result.failure(Exception("$e"));
    }
  }
}
