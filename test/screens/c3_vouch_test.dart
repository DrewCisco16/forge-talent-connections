import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/social/c3_vouch_flow.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// Signing a vouch celebrates, then points the person at the rewards program
/// with the honest caveat: points come from the backend once the vouch
/// verifies, never from the tap.
void main() {
  Future<void> pump(WidgetTester tester) async {
    tester.view.physicalSize = const Size(440, 3000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: buildForgeTheme(),
        home: MediaQuery(
          data: const MediaQueryData(
            size: Size(440, 3000),
            disableAnimations: true,
          ),
          child: const C3VouchFlow(),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets("before signing there is no celebration",
      (WidgetTester tester) async {
    await pump(tester);
    expect(find.textContaining("Sign My Vouch"), findsOneWidget);
    expect(find.text("Your vouch is sealed"), findsNothing);
  });

  testWidgets("signing seals the vouch and links to rewards",
      (WidgetTester tester) async {
    await pump(tester);
    // Reduced motion completes the hold on a single press.
    await tester.tap(find.textContaining("Sign My Vouch"));
    await tester.pump();
    expect(find.text("Your vouch is sealed"), findsOneWidget);
    expect(find.text("View Rewards & Referrals"), findsOneWidget);
    // The honest caveat ships with the celebration.
    expect(
      find.textContaining("never by the tap itself"),
      findsOneWidget,
    );
  });
}
