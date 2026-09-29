import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";

import "package:forge_talent_connections/widgets/core_loop_strip.dart";

import "../support/harness.dart";

void main() {
  testWidgets("the strip names the five steps in order under the rule", (
    WidgetTester tester,
  ) async {
    await pumpHarness(tester, const CoreLoopStrip());

    expect(CoreLoopStrip.steps, <String>[
      "Invitation",
      "Proof",
      "Vouch",
      "Project",
      "Sealed Record",
    ]);
    expect(find.text("How It Works"), findsOneWidget);
    for (int i = 0; i < CoreLoopStrip.steps.length; i++) {
      expect(find.text("${i + 1}"), findsOneWidget);
      expect(find.textContaining(CoreLoopStrip.steps[i]), findsOneWidget);
    }
    expect(
      find.text(
        "Nothing opens without proof. Two humans decide at every step.",
      ),
      findsOneWidget,
    );
  });

  testWidgets("the strip reflows at 2.0x text scale instead of clipping", (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await pumpHarness(
      tester,
      const MediaQuery(
        data: MediaQueryData(textScaler: TextScaler.linear(2.0)),
        child: SingleChildScrollView(child: CoreLoopStrip()),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.textContaining("Sealed Record"), findsOneWidget);
  });
}
