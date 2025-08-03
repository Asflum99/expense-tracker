import 'package:expense_tracker/utils/result.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:app_links/app_links.dart';
import 'dart:async';
import 'package:url_launcher/url_launcher.dart';

sealed class AuthStatus {}

class Authenticated extends AuthStatus {}

class Unauthenticated extends AuthStatus {}

class Error extends AuthStatus {
  final String message;
  Error(this.message);
}

class GmailBackend {
  final apiUrl = dotenv.get("API_URL");
  Future<Result<String>> setupGmailAccess(String idToken) async {
    try {
      final status = await _isUserAlreadyAuth(idToken);
      return switch (status) {
        Authenticated() => Result.success("authenticated"),
        Unauthenticated() => await _authNewUser(idToken),
        Error(message: final msg) => Result.failure(Exception(msg)),
      };
    } catch (e) {
      return Result.failure(Exception("Ocurrió un error inesperado: $e"));
    }
  }

  Future<Result<String>> _authNewUser(String idToken) async {
    final response = await _getHttpResponse(idToken, 'google');
    try {
      final authUrl = jsonDecode(response.body)['auth_url'];
      final completer = Completer<Result<String>>();
      final appLinks = AppLinks();

      StreamSubscription? sub;

      sub = appLinks.uriLinkStream.listen((uri) {
        if (uri.scheme == 'expense_tracker' && uri.host == 'auth_complete') {
          completer.complete(Result.success('authenticated'));
          sub?.cancel();
        }
      });

      launchUrl(Uri.parse(authUrl), mode: LaunchMode.externalApplication);

      return completer.future;
    } catch (e) {
      return Result.failure(
        Exception('Revise su conexión a internet e intente de nuevo.'),
      );
    }
  }

  Future<AuthStatus> _isUserAlreadyAuth(String idToken) async {
    final response = await _getHttpResponse(idToken, "status");

    try {
      final responseBody = jsonDecode(response.body);
      final success = responseBody["authenticated"];
      if (success) {
        return Authenticated();
      } else {
        return Unauthenticated();
      }
    } catch (e) {
      return Error("Revise su conexión a internet e intente de nuevo.");
    }
  }

  Future<http.Response> _getHttpResponse(String idToken, String task) async {
    final body = jsonEncode({"id_token": idToken});

    final url = Uri.parse('$apiUrl/users/auth/$task');

    return http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: body,
    );
  }
}
