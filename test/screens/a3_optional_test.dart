import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/onboarding/a3_choose_avatar.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// Avatars stay optional, reversible, and skippable. Matching never depends
/// on appearance, so the skip path is pinned.
void main() {
  testWidgets("A3 offers the skip path and states avatars are optional", (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(440, 3000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: buildForgeTheme(),
          home: MediaQuery(
            data: const MediaQueryData(
              size: Size(440, 3000),
              disableAnimations: true,
            ),
            child: const A3ChooseAvatar(),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.textContaining("Skip for now"), findsOneWidget);
    expect(find.textContaining("optional"), findsWidgets);
  });
}
