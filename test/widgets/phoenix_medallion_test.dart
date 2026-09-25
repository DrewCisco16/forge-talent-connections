import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/phoenix_medallion.dart";

/// The medallion is one asset in three roles, and every role is a still
/// frame under reduced motion.
void main() {
  Future<void> pump(
    WidgetTester tester,
    Widget child, {
    bool reducedMotion = false,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildForgeTheme(),
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: reducedMotion),
          child: Scaffold(body: Center(child: child)),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets("the mark breathes, and holds still under reduced motion", (
    WidgetTester tester,
  ) async {
    await pump(tester, const PhoenixMedallion(height: 96));
    final Finder breath = find.descendant(
      of: find.byType(PhoenixMedallion),
      matching: find.byType(Transform),
    );
    expect(breath, findsOneWidget);
    expect(find.bySemanticsLabel(RegExp("phoenix medallion")), findsOneWidget);
    // The shine: a sweep painted only on the metal, plus sparkle points.
    expect(
      find.descendant(
        of: find.byType(PhoenixMedallion),
        matching: find.byType(ShaderMask),
      ),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: find.byType(PhoenixMedallion),
        matching: find.byType(CustomPaint),
      ),
      findsWidgets,
    );

    await pump(tester, const PhoenixMedallion(height: 96), reducedMotion: true);
    expect(breath, findsNothing);
    // Reduced motion keeps one resting highlight and drops the sparkles.
    expect(
      find.descendant(
        of: find.byType(PhoenixMedallion),
        matching: find.byType(ShaderMask),
      ),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: find.byType(PhoenixMedallion),
        matching: find.byType(CustomPaint),
      ),
      findsNothing,
    );
  });

  testWidgets("the pending state names what is being checked", (
    WidgetTester tester,
  ) async {
    await pump(tester, const MedallionPending(label: "Loading projects"));
    final Finder pulse = find.descendant(
      of: find.byType(MedallionPending),
      matching: find.byType(FadeTransition),
    );
    expect(find.text("Loading projects"), findsOneWidget);
    expect(pulse, findsOneWidget);

    await pump(
      tester,
      const MedallionPending(label: "Loading projects"),
      reducedMotion: true,
    );
    expect(pulse, findsNothing);
    expect(find.text("Loading projects"), findsOneWidget);
  });

  testWidgets("the empty state offers at most one way forward", (
    WidgetTester tester,
  ) async {
    int taps = 0;
    await pump(
      tester,
      EmptyState(
        title: "No projects matched your search",
        body: "Nothing is hidden. Clear the search to see all 6.",
        actionLabel: "Clear Search",
        onAction: () => taps++,
      ),
    );
    expect(find.text("No projects matched your search"), findsOneWidget);
    await tester.tap(find.text("Clear Search"));
    expect(taps, 1);

    await pump(
      tester,
      const EmptyState(title: "Nothing yet", body: "Come back after a seal."),
    );
    expect(find.text("Clear Search"), findsNothing);
  });
}
