import 'dart:convert';
import 'dart:io';
import 'package:expense_tracker/utils/result.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';

class GmailService {
  static Future<Result<String>> readMessages(String sessionToken) async {
    try {
      // LÓGICA QUE MOVERÉ LUEGO
      final DateTime now = DateTime.now();
      final String formattedDate = DateFormat('yyyy-MM-dd HH:mm:ss').format(now);
      // LÓGICA QUE MOVERÉ LUEGO

      final String apiUrl = const String.fromEnvironment('API_URL');
      final response = await http.get(
        Uri.parse('$apiUrl/gmail/read-messages'),
        headers: {
          'Authorization': 'Bearer $sessionToken',
          'Content-Type': 'application/json',
          'Device-Time': formattedDate
        },
      );

      if (response.statusCode == 200) {
        return Result.success(response.body);
      } else {
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
      return Result.failure(Exception("No hay conexión a internet."));
    } catch (e) {
      return Result.failure(Exception("$e"));
    }
  }
}
