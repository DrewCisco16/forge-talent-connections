import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/internal_fire.dart";

/// The internal fire burns inside its own bounds, and goes still under
/// reduced motion instead of running a hidden ticker.
void main() {
  Widget host({required bool reducedMotion}) => MaterialApp(
    theme: buildForgeTheme(),
    home: MediaQuery(
      data: MediaQueryData(disableAnimations: reducedMotion),
      child: const Scaffold(
        body: Center(
          child: SizedBox(
            width: 300,
            height: 120,
            child: ForgeInternalFireContainer(child: Text("Streak")),
          ),
        ),
      ),
    ),
  );

  testWidgets("renders the child over the fire surface and animates", (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(host(reducedMotion: false));
    expect(find.text("Streak"), findsOneWidget);
    expect(
      find.descendant(
        of: find.byType(ForgeInternalFireContainer),
        matching: find.byType(CustomPaint),
      ),
      findsWidgets,
    );
    expect(tester.hasRunningAnimations, isTrue);
  });

  testWidgets("reduced motion: a still frame, no running ticker", (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(host(reducedMotion: true));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text("Streak"), findsOneWidget);
    expect(tester.hasRunningAnimations, isFalse);
  });
}
