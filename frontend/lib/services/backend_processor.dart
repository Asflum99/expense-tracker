import 'package:expense_tracker/utils/result.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class BackendProcessor {
  Future<Result<String>> processMessages(List<Map<String, dynamic>> messages) async {
    try {
      final String apiUrl = const String.fromEnvironment('API_URL');
      final body = jsonEncode(messages);

      final url = Uri.parse('$apiUrl/process-expenses');

      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: body,
      );

      if (response.statusCode == 200) {
        return Result.success(response.body);
      } else {
        return Result.failure(
          Exception("Error del servidor: ${response.body}"),
        );
      }
    } catch (e) {
      return Result.failure(Exception("Ocurrio un error inesperado: $e"));
    }
  }
}