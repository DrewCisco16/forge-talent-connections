import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/social/c6_rewards.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/providers.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// The rewards program is fail-closed like everything else.
///
/// Points come only from verified events, pending points never count as
/// paid, and an integrity hold freezes the account visibly instead of
/// leaving a payout path that might appear to work. The fair-play rules -
/// human-earned points only, audits before every award - ship on the screen
/// itself, not in a footnote.
void main() {
  Future<void> pump(WidgetTester tester, DemoScenario scenario) async {
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
            child: const C6Rewards(),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets("verified: active account with verified points and prizes", (
    WidgetTester tester,
  ) async {
    await pump(tester, DemoScenario.verified);
    expect(find.text("340"), findsOneWidget);
    expect(find.textContaining("Top 12% this quarter"), findsWidgets);
    expect(find.text("Yearly car giveaway"), findsOneWidget);
    expect(find.text("Share My Code"), findsOneWidget);
    // The fair-play rules are on the screen, not hidden.
    expect(find.textContaining("AI agent"), findsWidgets);
    expect(find.textContaining("human audit"), findsWidgets);
    expect(find.textContaining("No purchase"), findsOneWidget);
  });

  testWidgets("pending: waiting points are shown as pending, never as paid", (
    WidgetTester tester,
  ) async {
    await pump(tester, DemoScenario.pending);
    expect(find.text("240"), findsOneWidget);
    expect(find.textContaining("100 pending verification"), findsOneWidget);
    expect(
      find.textContaining("count only when the checks pass"),
      findsOneWidget,
    );
  });

  testWidgets("denied: the freeze is stated with the human-review path", (
    WidgetTester tester,
  ) async {
    await pump(tester, DemoScenario.denied);
    expect(find.text("0"), findsOneWidget);
    expect(find.textContaining("Points frozen"), findsOneWidget);
    expect(
      find.textContaining("Standing suspended during the hold"),
      findsWidgets,
    );
    expect(
      find.textContaining("until a person reviews the hold"),
      findsOneWidget,
    );
  });
}
