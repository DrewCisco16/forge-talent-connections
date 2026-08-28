import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/providers.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

import "screen_catalog.dart";

/// Accessibility text scaling.
///
/// iOS lets a user enlarge every label in the system. A layout that only holds
/// at the default size is not accessible: it clips the very text the setting
/// exists to make readable. The SOP requires the edges be tested, not just the
/// happy path.
///
/// 1.3 is a realistic large-text setting. Anything beyond roughly this needs a
/// reflowing layout rather than a scaled one, which is a design decision, not
/// a code fix — so this pins the range the current design is expected to hold.
void main() {
  const double scale = 1.3;
  const Size phone = Size(440, 956);

  group("layout holds at ${scale}x text scale", () {
    for (final MapEntry<String, Widget> screen in screenCatalog.entries) {
      testWidgets(screen.key, (WidgetTester tester) async {
        tester.view.physicalSize = phone;
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.reset);

        await tester.pumpWidget(
          ProviderScope(
            overrides: <Override>[
              demoScenarioProvider
                  .overrideWith((Ref ref) => DemoScenario.verified),
            ],
            child: MaterialApp(
              theme: buildForgeTheme(),
              home: MediaQuery(
                data: const MediaQueryData(
                  size: phone,
                  disableAnimations: true,
                  textScaler: TextScaler.linear(scale),
                ),
                child: screen.value,
              ),
            ),
          ),
        );
        await tester.pump(const Duration(milliseconds: 400));
        await tester.pump(const Duration(milliseconds: 400));

        expect(
          tester.takeException(),
          isNull,
          reason: "${screen.key} clips or overflows at ${scale}x text scale",
        );
      });
    }
  });
}
