import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/onboarding/a5_elevator_pitch.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// The ad's on-screen text is restated in sharp native type below the
/// player, honestly labelled, so the message is readable regardless of the
/// source video's resolution.
void main() {
  testWidgets("A5 carries the restated ad text band", (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(440, 4600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: buildForgeTheme(),
          home: MediaQuery(
            data: const MediaQueryData(
              size: Size(440, 4600),
              disableAnimations: true,
            ),
            child: const A5ElevatorPitch(),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));

    // The honest label and the opening caption (idle state) are present.
    expect(find.text("AD TEXT · RESTATED FOR CLARITY"), findsOneWidget);
    expect(
      find.text(
        "FORGE Talent Connections. Provable trust for every connection.",
      ),
      findsOneWidget,
    );
  });
}
