import 'package:flutter/material.dart';
import 'package:expense_tracker/services/gmail_access_manager.dart';
import 'package:expense_tracker/services/gmail_expense_sync_manager.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

Future main() async {
  tz.initializeTimeZones();
  tz.setLocalLocation(tz.getLocation('America/Lima'));
  await dotenv.load(fileName: ".env");
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
  void _authenticateAndSetup() async {
    final tokenResult = await GmailAccessManager.authenticateAndSetup();

    if (!mounted) return;

    if (tokenResult.isFailure) {
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("${syncResult.exceptionOrNull()}")),
      );
    } else {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(syncResult.getOrNull()!)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
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
    );
  }
}
