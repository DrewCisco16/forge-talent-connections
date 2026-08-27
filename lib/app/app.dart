import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "router.dart";

/// The application shell.
class ForgeApp extends StatefulWidget {
  const ForgeApp({super.key});

  @override
  State<ForgeApp> createState() => _ForgeAppState();
}

class _ForgeAppState extends State<ForgeApp> {
  late final router = buildRouter();

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: "FORGE Talent Connections",
      debugShowCheckedModeBanner: false,
      theme: buildForgeTheme(),
      routerConfig: router,
    );
  }
}
