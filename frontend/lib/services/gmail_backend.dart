import 'package:expense_tracker/utils/result.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
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
      return Result.failure(Exception("$e"));
    }
  }

  Future<Result<String>> _authNewUser(String idToken) async {
    try {
      final response = await _getHttpResponse(idToken, 'google');
      final responseData = jsonDecode(response.body);
      final authUrl = responseData['auth_url'];
      final sessionId = responseData['session_id'];

      launchUrl(Uri.parse(authUrl), mode: LaunchMode.externalApplication);

      // Polling cada 2 segundos
      for (int i = 0; i < 60; i++) {
        // 2 minutos máximo
        await Future.delayed(Duration(seconds: 2));

        final statusResponse = await http.get(
          Uri.parse('$apiUrl/users/auth/status/$sessionId'),
        );

        if (statusResponse.statusCode == 200) {
          final status = jsonDecode(statusResponse.body)['status'];

          if (status == 'completed') {
            return Result.success('authenticated');
          }
        }
      }

      return Result.failure(Exception('Timeout de autenticación'));
    } catch (e) {
      return Result.failure(Exception('$e'));
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
