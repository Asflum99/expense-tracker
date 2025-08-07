import 'dart:convert';
import 'dart:io';
import 'package:expense_tracker/utils/result.dart';
import 'package:http/http.dart' as http;

class GmailService {  
  static Future<Result<String>> readMessages(String idToken) async {
    try {
      final String apiUrl = const String.fromEnvironment('API_URL');
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
        // Capturar detalles específicos del error del servidor
        String errorDetail = "Server Error (${response.statusCode}): ";
        try {
          final errorBody = jsonDecode(response.body);
          errorDetail += errorBody['detail'] ?? response.body;
        } catch (e) {
          errorDetail += response.body;
        }
        
        return Result.failure(Exception(errorDetail));
      }
    } on SocketException {
      return Result.failure(
        Exception("No hay conexión a internet."),
      );
    } catch (e) {
      return Result.failure(Exception("$e"));
    }
  }
}