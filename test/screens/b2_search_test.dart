import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/core/b2_find_opportunities.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/providers.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// The B2 search is a live linear search over the served project list.
///
/// Multiple matches all render; a miss renders the explicit not-found
/// state - never a silent blank.
void main() {
  Future<void> pump(WidgetTester tester) async {
    tester.view.physicalSize = const Size(440, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          demoScenarioProvider.overrideWith((Ref ref) => DemoScenario.verified),
        ],
        child: MaterialApp(
          theme: buildForgeTheme(),
          home: MediaQuery(
            data: const MediaQueryData(
              size: Size(440, 2000),
              disableAnimations: true,
            ),
            child: const B2FindOpportunities(),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets("empty query shows every project", (WidgetTester tester) async {
    await pump(tester);
    expect(find.text("${kOpportunities.length} projects"), findsOneWidget);
    expect(find.text("Employment Law Presentation"), findsOneWidget);
  });

  testWidgets("a query narrows to its matches and reports the count", (
    WidgetTester tester,
  ) async {
    await pump(tester);
    await tester.enterText(find.byType(TextField), "law");
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text("1 of ${kOpportunities.length} projects"), findsOneWidget);
    expect(find.text("Employment Law Presentation"), findsOneWidget);
    expect(find.text("Business Analytics Capstone Dashboard"), findsNothing);
  });

  testWidgets("no match renders the explicit not-found state", (
    WidgetTester tester,
  ) async {
    await pump(tester);
    await tester.enterText(find.byType(TextField), "zzz-nothing");
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text("No projects matched your search"), findsOneWidget);
    expect(find.text("0 of ${kOpportunities.length} projects"), findsOneWidget);
  });
}
