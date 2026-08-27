import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

void main() {
  runApp(const ProviderScope(child: ForgeApp()));
}

/// Root application widget.
///
/// The theme is intentionally not defined here yet: it must be derived from
/// design_tokens.json, which has not been delivered to this repo. See the
/// milestone report rather than substituting placeholder values.
class ForgeApp extends StatelessWidget {
  const ForgeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      title: "FORGE Talent Connections",
      home: Scaffold(body: SizedBox.shrink()),
    );
  }
}
