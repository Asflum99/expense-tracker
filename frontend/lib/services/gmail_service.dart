import 'dart:convert';
import 'dart:io';
import 'package:expense_tracker/utils/result.dart';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'dart:typed_data';

class GmailService {
  static Future<Result<Uint8List>> readMessages(String sessionToken) async {
    try {
      // LÓGICA QUE MOVERÉ LUEGO
      final DateTime now = DateTime.now();
      final String formattedDate = DateFormat(
        'yyyy-MM-dd HH:mm:ss',
      ).format(now);
      // LÓGICA QUE MOVERÉ LUEGO

      final String apiUrl = const String.fromEnvironment('API_URL');
      final response = await http.get(
        Uri.parse('$apiUrl/gmail/get-gmail-messages'),
        headers: {
          'Authorization': 'Bearer $sessionToken',
          'Device-Time': formattedDate,
        },
      );

      if (response.statusCode == 200) {
        return Result.success(response.bodyBytes); // Cambio aquí
      } else {
        final errorBody = jsonDecode(response.body);
        return Result.failure(Exception(errorBody));
      }
    } on SocketException {
      return Result.failure(Exception("No hay conexión a internet."));
    } catch (e) {
      return Result.failure(Exception("$e"));
    }
  }
}
