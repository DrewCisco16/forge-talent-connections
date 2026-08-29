import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/app/router.dart";
import "package:forge_talent_connections/features/onboarding/mission.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/operator_footer.dart";
import "package:go_router/go_router.dart";

/// The Mission and Purpose statement sits after the door pages: sign-in
/// continues through it, the role screen continues through it, and its copy
/// removes ambiguity about what FORGE Talent Connections is and is not.
void main() {
  late GoRouter router;

  Future<void> pumpApp(WidgetTester tester) async {
    tester.view.physicalSize = const Size(440, 4000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    router = buildRouter();
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(
          theme: buildForgeTheme(),
          routerConfig: router,
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

  Future<void> settle(WidgetTester tester) async {
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets("sign-in continues through the mission statement", (
    WidgetTester tester,
  ) async {
    await pumpApp(tester);
    router.go("/sign-in");
    await settle(tester);
    await tester.tap(find.text("Sign In"));
    await settle(tester);
    expect(find.text("Our Mission"), findsOneWidget);
    await tester.tap(find.text("Continue to FORGE Talent Connections"));
    await settle(tester);
    expect(find.textContaining("Welcome Back,"), findsWidgets);
  });

  testWidgets("the mission copy removes the ambiguity", (
    WidgetTester tester,
  ) async {
    await pumpApp(tester);
    router.go("/mission");
    await settle(tester);
    // Scoped to the mission screen: the splash can linger in the tree
    // while its exit transition finishes.
    Finder onMission(Finder f) =>
        find.descendant(of: find.byType(MissionScreen), matching: f);
    // The purpose, stated as one sentence.
    expect(
      onMission(
        find.textContaining(
          "to connect Talent with Opportunity through provable trust",
        ),
      ),
      findsOneWidget,
    );
    // The category boundary, both directions.
    expect(
      onMission(find.textContaining("invite-only project collaboration")),
      findsOneWidget,
    );
    expect(onMission(find.textContaining("not a job board")), findsOneWidget);
    // The settled vocabulary, each named.
    expect(onMission(find.text("Talent")), findsOneWidget);
    expect(onMission(find.text("Opportunity")), findsOneWidget);
    expect(onMission(find.text("Veteran")), findsOneWidget);
    // The two-human standard.
    expect(
      onMission(find.textContaining("Nothing here replaces two humans")),
      findsOneWidget,
    );
    // The operating company closes the page.
    expect(onMission(find.byType(OperatorFooter)), findsOneWidget);
  });
}
