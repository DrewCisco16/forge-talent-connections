import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/trust/d3_sign_in.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/burning_flame.dart";

/// The brand mark burns everywhere it appears full-size: the sign-in
/// screen carries the same asymmetric flame animation as the splash.
void main() {
  testWidgets("sign-in mounts the burning flame behind the mark",
      (WidgetTester tester) async {
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
    expect(find.byType(BurningFlame), findsOneWidget);
  });
}
