import 'package:credential_manager/credential_manager.dart';
import 'package:expense_tracker/utils/result.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class GoogleAuthHandler {
  static final CredentialManager _credentialManager = CredentialManager();

  static Future<Result<String>> getUserIdToken() async {
    try {
      if (_credentialManager.isSupportedPlatform) {
        await _credentialManager.init(
          preferImmediatelyAvailableCredentials: true,
          googleClientId: dotenv.get("WEB_CLIENT_ID"),
        );
      }

      final GoogleIdTokenCredential? credential = await _credentialManager
          .saveGoogleCredential(useButtonFlow: false);

      final idToken = credential?.idToken;

      if (idToken == null) {
        return Result.failure(Exception("No se obtuvo el ID Token."));
      }

      return Result.success(idToken);
    } on CredentialException catch (_) {
      return Result.failure(Exception("Error al guardar la credencial"));
    } catch (e) {
      return Result.failure(Exception("Error inesperado: $e"));
    }
  }
}
