import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/providers.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/bottom_nav.dart";

import "screen_catalog.dart";

/// Logical viewports the demo has to survive.
///
/// The 17 Pro Max is the demo target. The smaller sizes are here so a layout
/// that only works on the largest phone cannot pass: an overflow on a 6.1"
/// device is still a bug, and the design baseline is 390 wide.
const Map<String, Size> _viewports = <String, Size>{
  "iPhone 17 Pro Max 440x956": Size(440, 956),
  "iPhone 17 Pro 402x874": Size(402, 874),
  "design baseline 390x844": Size(390, 844),
  "iPhone SE 375x667": Size(375, 667),
};

void main() {
  group("no overflow at any supported phone size", () {
    for (final MapEntry<String, Size> vp in _viewports.entries) {
      for (final MapEntry<String, Widget> screen in screenCatalog.entries) {
        testWidgets("${screen.key} · ${vp.key}", (WidgetTester tester) async {
          tester.view.physicalSize = vp.value;
          tester.view.devicePixelRatio = 1.0;
          addTearDown(tester.view.reset);

          await tester.pumpWidget(
            ProviderScope(
              overrides: <Override>[
                demoScenarioProvider.overrideWith(
                  (Ref ref) => DemoScenario.verified,
                ),
              ],
              child: MaterialApp(
                theme: buildForgeTheme(),
                home: MediaQuery(
                  data: MediaQueryData(
                    size: vp.value,
                    disableAnimations: true,
                    // A phone with a Dynamic Island: content must clear it.
                    padding: const EdgeInsets.only(top: 59, bottom: 34),
                  ),
                  child: Scaffold(
                    body: screen.value,
                    bottomNavigationBar: BottomNav(
                      current: ForgeTab.home,
                      onSelected: (_) {},
                    ),
                  ),
                ),
              ),
            ),
          );
          await tester.pump(const Duration(milliseconds: 400));
          await tester.pump(const Duration(milliseconds: 400));

          // A RenderFlex overflow is reported as an exception by the framework,
          // so this catches clipped content as well as outright failures.
          expect(
            tester.takeException(),
            isNull,
            reason: "${screen.key} overflows at ${vp.key}",
          );
        });
      }
    }
  });
}
