import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/social_action.dart";

/// A signature is recorded exactly once. Repeated presses, repeated holds,
/// and reduced-motion completion must never fire the callback twice.
void main() {
  Future<void> pump(
    WidgetTester tester, {
    required bool reducedMotion,
    required void Function() onCompleted,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildForgeTheme(),
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: reducedMotion),
          child: Scaffold(
            body: Center(
              child: HoldToSignVouch(
                label: "Sign My Vouch",
                onCompleted: onCompleted,
              ),
            ),
          ),
        ),
      ),
    );
  }

  testWidgets("reduced motion: repeated taps fire the callback once", (
    WidgetTester tester,
  ) async {
    int fired = 0;
    await pump(tester, reducedMotion: true, onCompleted: () => fired++);
    await tester.tap(find.byType(HoldToSignVouch));
    await tester.pump();
    await tester.tap(find.byType(HoldToSignVouch));
    await tester.pump();
    await tester.tap(find.byType(HoldToSignVouch));
    await tester.pump();
    expect(fired, 1);
  });

  testWidgets("normal motion: a completed hold plus a second hold fires once", (
    WidgetTester tester,
  ) async {
    int fired = 0;
    await pump(tester, reducedMotion: false, onCompleted: () => fired++);

    final Offset center = tester.getCenter(find.byType(HoldToSignVouch));
    final TestGesture hold = await tester.startGesture(center);
    // First pump lets the tap-down land and the sweep start; the second
    // carries the controller past its full duration.
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 1300));
    await hold.up();
    await tester.pump();
    expect(fired, 1);

    final TestGesture again = await tester.startGesture(center);
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 1300));
    await again.up();
    await tester.pump();
    expect(fired, 1, reason: "a second hold must not re-fire");
  });

  testWidgets("an early release records nothing", (WidgetTester tester) async {
    int fired = 0;
    await pump(tester, reducedMotion: false, onCompleted: () => fired++);
    final Offset center = tester.getCenter(find.byType(HoldToSignVouch));
    final TestGesture hold = await tester.startGesture(center);
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 300));
    await hold.up();
    await tester.pump(const Duration(milliseconds: 1500));
    expect(fired, 0);
  });
}
