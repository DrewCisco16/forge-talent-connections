import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/onboarding/a5_elevator_pitch.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/providers.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// The AI Pitch Studio's confidence gate is fail-closed.
///
/// A likeness is generated only when the backend reports at least the
/// required confidence. Below the line, or while the check is running, the
/// generate action must not exist in an enabled state — a locked control
/// that could appear to work would be the exact dishonesty the product
/// exists to prevent.
void main() {
  Future<void> pump(WidgetTester tester, DemoScenario scenario) async {
    tester.view.physicalSize = const Size(440, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          demoScenarioProvider.overrideWith((Ref ref) => scenario),
        ],
        child: MaterialApp(
          theme: buildForgeTheme(),
          home: MediaQuery(
            data: const MediaQueryData(
              size: Size(440, 2400),
              disableAnimations: true,
            ),
            child: const A5ElevatorPitch(),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets("verified: generation is offered", (WidgetTester tester) async {
    await pump(tester, DemoScenario.verified);
    expect(find.text("Generate My AI Pitch"), findsOneWidget);
    expect(find.text("Generation locked"), findsNothing);
  });

  testWidgets("pending: locked while the likeness check runs",
      (WidgetTester tester) async {
    await pump(tester, DemoScenario.pending);
    expect(find.text("Generation locked"), findsOneWidget);
    expect(find.text("Generate My AI Pitch"), findsNothing);
  });

  testWidgets("denied: below the required confidence nothing is offered",
      (WidgetTester tester) async {
    await pump(tester, DemoScenario.denied);
    expect(find.text("Generation locked"), findsOneWidget);
    expect(find.text("Generate My AI Pitch"), findsNothing);
    // The refusal explains itself with the real numbers.
    expect(
      find.textContaining("88 is below the required 95"),
      findsOneWidget,
    );
  });
}
