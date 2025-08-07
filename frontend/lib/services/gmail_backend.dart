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
        final responseData = jsonDecode(response.body);
        final String authUrl = responseData["auth_url"];
        if (authUrl.isNotEmpty) {
          final sessionId = responseData['session_id'];

          await launchUrl(
            Uri.parse(authUrl),
            mode: LaunchMode.externalApplication,
          );

          final sessionToken = await _pollForAuthCompletion(sessionId);
          return Result.success(sessionToken);
        } else {
          final sessionToken = responseData['session_token'];
          return Result.success(sessionToken);
        }
      } else {
        return Result.failure(Exception('Error de autenticación'));
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
