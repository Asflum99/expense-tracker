import 'package:flutter/material.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;
import 'services/google_auth_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:expense_tracker/services/gmail_expense_sync_manager.dart';

Future main() async {
  tz.initializeTimeZones();
  tz.setLocalLocation(tz.getLocation('America/Lima'));

  runApp(const ExpenseTrackerApp());
}

class ExpenseTrackerApp extends StatelessWidget {
  const ExpenseTrackerApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Expense Tracker',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
      ),
      home: const HomePage(title: 'Expense Tracker'),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.title});
  final String title;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool _isLoading = false;
  String? _sessionToken;

  @override
  void initState() {
    super.initState();
    _loadStoredToken();
  }

  Future<void> _loadStoredToken() async {
    final prefs = await SharedPreferences.getInstance();
    _sessionToken = prefs.getString('session_token');
  }

  void _handleRegisterExpenses() async {
    setState(() {
      _isLoading = true;
    });

    if (_sessionToken != null && await _isTokenValid(_sessionToken!)) {
      _navigateToExpenseRegistration();
    } else {
      await _authenticateAndSetup();
    }
  }

  Future<bool> _isTokenValid(String token) async {
    try {
      final parts = token.split('.');
      final payload = json.decode(
        utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))),
      );
      final exp = payload['exp'] * 1000;
      return DateTime.now().millisecondsSinceEpoch < exp;
    } catch (e) {
      return false;
    }
  }

  void _navigateToExpenseRegistration() async {
    final syncResult = await GmailExpenseSyncManager.syncAndDownloadExpenses(
      _sessionToken!,
    );

    if (!mounted) return;

    if (syncResult.isFailure) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("${syncResult.exceptionOrNull()}")),
      );
    } else {
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("CSV guardado en la carpeta Descargas")),
      );
    }
  }

  Future<void> _authenticateAndSetup() async {
    final authResult = await GoogleAuthHandler.authenticationAndSetupAccess();

    if (!mounted) return;

    if (authResult.isFailure) {
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("${authResult.exceptionOrNull()}")),
      );
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final token = authResult.getOrNull()!;
    await prefs.setString('session_token', token);

    setState(() {
      _sessionToken = token;
    });

    _navigateToExpenseRegistration();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 300),
                  child: ElevatedButton(
                    onPressed: _handleRegisterExpenses,
                    style: ButtonStyle(
                      foregroundColor: WidgetStateProperty.all(Colors.black),
                      backgroundColor: WidgetStateProperty.all(
                        const Color.fromARGB(255, 223, 223, 223),
                      ),
                    ),
                    child: const Text("Registrar gastos"),
                  ),
                ),
              ],
            ),
          ),
          if (_isLoading)
            Center(
              child: Padding(
                padding: const EdgeInsets.only(top: 220),
                child: const CircularProgressIndicator(),
              ),
            ),
        ],
      ),
    );
  }
}
