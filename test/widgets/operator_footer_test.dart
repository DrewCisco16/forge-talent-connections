import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/onboarding/a1_splash.dart";
import "package:forge_talent_connections/features/onboarding/legal_terms.dart";
import "package:forge_talent_connections/features/trust/d3_sign_in.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/operator_footer.dart";
import "package:go_router/go_router.dart";

/// The operating company's mark closes the brand and legal surfaces: the
/// FORGE LINK LLC logo, small at the foot of the page, with the ownership
/// line and the accurate corporate facts - incorporated in Delaware,
/// headquartered in Doral, Florida.
void main() {
  Future<void> pumpScreen(WidgetTester tester, Widget screen) async {
    tester.view.physicalSize = const Size(440, 4600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(
          theme: buildForgeTheme(),
          routerConfig: GoRouter(
            routes: <RouteBase>[
              GoRoute(
                path: "/",
                builder: (_, __) => MediaQuery(
                  data: const MediaQueryData(
                    size: Size(440, 4600),
                    disableAnimations: true,
                  ),
                  child: screen,
                ),
              ),
            ],
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  const String ownershipLine =
      "FORGE Talent Connections is owned and operated by FORGE LINK LLC";
  const String factsLine =
      "Incorporated in Delaware · Headquartered in Doral, Florida";

  for (final (String name, Widget screen) in <(String, Widget)>[
    ("sign-in", const D3SignIn()),
    ("splash", const A1Splash()),
    ("legal terms", const LegalTerms()),
  ]) {
    testWidgets("$name page carries the operating company footer", (
      WidgetTester tester,
    ) async {
      await pumpScreen(tester, screen);
      expect(find.byType(OperatorFooter), findsOneWidget);
      expect(find.text(ownershipLine), findsOneWidget);
      expect(find.text(factsLine), findsOneWidget);
      // The mark itself, with its accessible name.
      expect(
        find.descendant(
          of: find.byType(OperatorFooter),
          matching: find.bySemanticsLabel("FORGE LINK LLC"),
        ),
        findsOneWidget,
      );
    });
  }

  testWidgets("the footer mark stays small", (WidgetTester tester) async {
    await pumpScreen(tester, const D3SignIn());
    final Image mark = tester.widget<Image>(
      find.descendant(
        of: find.byType(OperatorFooter),
        matching: find.byType(Image),
      ),
    );
    expect(mark.height, lessThanOrEqualTo(36));
  });
}
