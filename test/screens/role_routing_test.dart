import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/app/router.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// One door, three paths: Talent builds a profile, Opportunity goes to
/// sponsored projects, Veteran starts with the service seal. The routing is
/// the category promise, so it is pinned.
void main() {
  Future<void> pumpApp(WidgetTester tester) async {
    tester.view.physicalSize = const Size(440, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(
          theme: buildForgeTheme(),
          routerConfig: buildRouter(),
          builder: (BuildContext context, Widget? child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(disableAnimations: true),
            child: child!,
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  Future<void> chooseAndContinue(WidgetTester tester, String role) async {
    await tester.tap(find.text(role));
    await tester.pump();
    await tester.tap(find.text("Continue"));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
    // Every path passes the Mission statement before its destination.
    expect(find.text("Our Mission"), findsOneWidget);
    await tester.tap(find.text("Continue to FORGE Talent Connections"));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets("Talent continues to profile creation", (
    WidgetTester tester,
  ) async {
    await pumpApp(tester);
    await chooseAndContinue(tester, "Talent");
    expect(find.text("Create Your Profile"), findsOneWidget);
  });

  testWidgets("Opportunity continues to sponsored projects", (
    WidgetTester tester,
  ) async {
    await pumpApp(tester);
    await chooseAndContinue(tester, "Opportunity");
    expect(find.text("Find Opportunities"), findsOneWidget);
  });

  testWidgets("Veteran continues to the veteran path", (
    WidgetTester tester,
  ) async {
    await pumpApp(tester);
    await chooseAndContinue(tester, "Veteran");
    expect(find.text("Veteran Verification"), findsWidgets);
  });
}
