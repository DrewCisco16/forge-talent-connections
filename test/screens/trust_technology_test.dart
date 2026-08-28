import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/trust/trust_technology.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

void main() {
  Future<void> pump(WidgetTester tester) async {
    tester.view.physicalSize = const Size(440, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: buildForgeTheme(),
          home: const MediaQuery(
            data: MediaQueryData(disableAnimations: true),
            child: TrustTechnology(),
          ),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets("displays the three technologies as features",
      (WidgetTester tester) async {
    await pump(tester);
    expect(find.text("AI that can't overstep"), findsOneWidget);
    expect(find.text("A record that can't be quietly changed"), findsOneWidget);
    expect(find.text("Exports that prove themselves"), findsOneWidget);
    expect(find.text("PATENT-PENDING TECHNOLOGY"), findsOneWidget);
  });

  testWidgets("each feature links to where it is visible in the app",
      (WidgetTester tester) async {
    await pump(tester);
    expect(find.text("See it: AI Match"), findsOneWidget);
    expect(find.text("See it: Trust Wallet"), findsOneWidget);
    expect(find.text("See it: Export"), findsOneWidget);
  });
}
