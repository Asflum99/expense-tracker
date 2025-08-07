import 'package:flutter/material.dart';
import 'package:expense_tracker/services/gmail_access_manager.dart';
import 'package:expense_tracker/services/gmail_expense_sync_manager.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

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

  void _authenticateAndSetup() async {
    setState(() {
      _isLoading = true;
    });

    final tokenResult = await GmailAccessManager.authenticateAndSetup();

    if (!mounted) return;

    if (tokenResult.isFailure) {
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("${tokenResult.exceptionOrNull()}")),
      );
      return;
    }

    final idToken = tokenResult.getOrNull();

    final syncResult = await GmailExpenseSyncManager.syncAndDownloadExpenses(
      idToken!,
    );

    if (!mounted) return;

    if (syncResult.isFailure) {
            setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("${syncResult.exceptionOrNull()}")),
      );
    } else {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(syncResult.getOrNull()!)));
    }

    setState(() {
      _isLoading = false;
    });
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
                    onPressed: _authenticateAndSetup,
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
                padding: const EdgeInsets.only(
                  top: 220,
                ),
                child: const CircularProgressIndicator(),
              ),
            ),
        ],
      ),
    );
  }
}
