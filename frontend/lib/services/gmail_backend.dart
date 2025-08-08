import 'package:expense_tracker/utils/result.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'package:url_launcher/url_launcher.dart';

class GmailBackend {
  final String apiUrl = const String.fromEnvironment('API_URL');
  Future<Result<String>> authenticateUserComplete(String idToken) async {
    try {
      final url = Uri.parse('$apiUrl/users/authenticate');
      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> responseData = jsonDecode(response.body);
        if (responseData.containsKey('auth_url')) {
          // ESCENARIO 1: Usuario no está registrado en la base de datos. Comenzar flujo de registro.
          final sessionId = responseData['session_id'];

          await launchUrl(
            Uri.parse(responseData['auth_url']),
            mode: LaunchMode.externalApplication,
          );

          final sessionToken = await _pollForAuthCompletion(sessionId);
          return Result.success(sessionToken);
        } else {
          // ESCENARIO 2: Usuario ya estaba registrado en la base de datos, pero tenía el JWT token vencido
          final sessionToken = responseData['session_token'];
          return Result.success(sessionToken);
        }
      } else {
        try {
          final Map<String, dynamic> errorData = jsonDecode(response.body);
          final errorMessage = errorData['detail'] ?? 'Error desconocido';
          return Result.failure(Exception(errorMessage));
        } catch (e) {
          return Result.failure(Exception(response.body));
        }
      }
    } catch (e) {
      return Result.failure(Exception('$e'));
    }
  }

  Future<String> _pollForAuthCompletion(String sessionId) async {
    for (int i = 0; i < 60; i++) {
      await Future.delayed(Duration(seconds: 2));

      final statusResponse = await http.get(
        Uri.parse('$apiUrl/users/auth/status/$sessionId'),
      );

      if (statusResponse.statusCode == 200) {
        final statusData = jsonDecode(statusResponse.body);

        if (statusData['status'] == 'completed') {
          return statusData['session_token'];
        }
      }
    }

    throw Exception('Timeout de autenticación');
  }
}
