import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/widgets/burning_flame.dart";

import "../support/harness.dart";

void main() {
  group("BurningFlame", () {
    testWidgets("burns: frames keep scheduling while animating",
        (WidgetTester tester) async {
      await tester.pumpWidget(
        harness(const BurningFlame(asset: "assets/brand/forge_flame_dark_bg.png")),
      );
      await tester.pump(const Duration(milliseconds: 100));
      // A repeating controller keeps a frame scheduled; a static widget
      // would have settled and stopped asking for frames.
      expect(tester.hasRunningAnimations, isTrue);
      // And time passing must not throw anywhere in the painter.
      await tester.pump(const Duration(milliseconds: 700));
      await tester.pump(const Duration(milliseconds: 700));
      expect(tester.takeException(), isNull);
    });

    testWidgets("respects reduced motion: no animation runs at all",
        (WidgetTester tester) async {
      await tester.pumpWidget(
        harness(
          const BurningFlame(asset: "assets/brand/forge_flame_dark_bg.png"),
          disableAnimations: true,
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));
      expect(tester.hasRunningAnimations, isFalse,
          reason: "reduced motion must render a still flame");
      expect(find.byType(Image), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets("the flame artwork is present in both modes",
        (WidgetTester tester) async {
      for (final bool reduced in <bool>[true, false]) {
        await tester.pumpWidget(
          harness(
            const BurningFlame(asset: "assets/brand/forge_flame_dark_bg.png"),
            disableAnimations: reduced,
          ),
        );
        await tester.pump(const Duration(milliseconds: 50));
        expect(find.byType(Image), findsOneWidget,
            reason: "the mark itself must render (reduced: $reduced)");
      }
    });
  });
}
