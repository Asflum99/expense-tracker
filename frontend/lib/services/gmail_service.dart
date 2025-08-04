import 'dart:convert';
import 'dart:io';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:expense_tracker/utils/result.dart';
import 'package:http/http.dart' as http;

class GmailService {
  final apiUrl = dotenv.get("API_URL");
  Future<Result<String>> readMessages(String idToken) async {
    try {
      final body = jsonEncode({"id_token": idToken});

      final url = Uri.parse('$apiUrl/gmail/read-messages');

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
    } on SocketException {
      return Result.failure(
        Exception("Revise su conexión a internet e intente de nuevo."),
      );
    } catch (e) {
      return Result.failure(Exception("Ocurrio un error inesperado: $e"));
    }
  }
}
