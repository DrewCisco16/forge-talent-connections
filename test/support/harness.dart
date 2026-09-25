import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// Wraps [child] in the application theme on the standard dark background.
///
/// [disableAnimations] drives the same MediaQuery flag the platform sets when
/// the user has asked for reduced motion, so tests can assert that a widget
/// stays correct without its animation.
Widget harness(
  Widget child, {
  double width = 390,
  bool disableAnimations = false,
}) {
  return MediaQuery(
    data: MediaQueryData(disableAnimations: disableAnimations),
    child: MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: buildForgeTheme(),
      home: Scaffold(
        backgroundColor: const Color(0xFF0F1A33),
        body: Center(
          child: SizedBox(
            width: width,
            child: Padding(padding: const EdgeInsets.all(16), child: child),
          ),
        ),
      ),
    ),
  );
}

/// Pumps [child] in the harness and settles pending frames.
Future<void> pumpHarness(
  WidgetTester tester,
  Widget child, {
  double width = 390,
  bool disableAnimations = false,
}) async {
  await tester.pumpWidget(
    harness(child, width: width, disableAnimations: disableAnimations),
  );
  await tester.pumpAndSettle();
}
