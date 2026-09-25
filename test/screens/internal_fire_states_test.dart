import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/core/b1_dashboard.dart";
import "package:forge_talent_connections/features/social/c6_rewards.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/providers.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/internal_fire.dart";

/// The internal fire is earned, never decorative: it burns only for a
/// living streak and verified points. A paused streak or a frozen account
/// keeps the plain card, because celebration is never painted over a hold.
void main() {
  Future<void> pump(
    WidgetTester tester,
    Widget screen,
    DemoScenario scenario,
  ) async {
    tester.view.physicalSize = const Size(440, 4200);
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
              size: Size(440, 4200),
              disableAnimations: true,
            ),
            child: screen,
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets("an active streak burns on the dashboard", (
    WidgetTester tester,
  ) async {
    await pump(tester, const B1Dashboard(), DemoScenario.verified);
    expect(find.byType(ForgeInternalFireContainer), findsOneWidget);
  });

  testWidgets("a paused streak stays a plain card", (
    WidgetTester tester,
  ) async {
    await pump(tester, const B1Dashboard(), DemoScenario.denied);
    expect(find.byType(ForgeInternalFireContainer), findsNothing);
  });

  testWidgets("verified points burn on the rewards card", (
    WidgetTester tester,
  ) async {
    await pump(tester, const C6Rewards(), DemoScenario.verified);
    expect(find.byType(ForgeInternalFireContainer), findsOneWidget);
  });

  testWidgets("a frozen account never gets the fire", (
    WidgetTester tester,
  ) async {
    await pump(tester, const C6Rewards(), DemoScenario.denied);
    expect(find.byType(ForgeInternalFireContainer), findsNothing);
  });
}
