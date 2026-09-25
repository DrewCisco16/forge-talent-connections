import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/trust/d3_sign_in.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/phoenix_medallion.dart";

/// The door pages share one identity mark: the sign-in screen carries the
/// phoenix medallion, the same mark as the splash and the mission page.
void main() {
  testWidgets("sign-in mounts the phoenix medallion as its mark", (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(440, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: buildForgeTheme(),
        home: MediaQuery(
          data: const MediaQueryData(
            size: Size(440, 2400),
            disableAnimations: true,
          ),
          child: const D3SignIn(),
        ),
      ),
    );
    await tester.pump();
    expect(find.byType(PhoenixMedallion), findsOneWidget);
  });
}
