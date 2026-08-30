import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/widgets/gold_button.dart";

import "../support/harness.dart";

void main() {
  testWidgets("GoldButton fires its callback when enabled", (
    WidgetTester tester,
  ) async {
    int taps = 0;
    await pumpHarness(
      tester,
      GoldButton(label: "Apply", onPressed: () => taps++),
    );
    await tester.tap(find.text("Apply"));
    expect(taps, 1);
  });

  testWidgets("GoldButton with a null callback cannot be actioned", (
    WidgetTester tester,
  ) async {
    await pumpHarness(
      tester,
      const GoldButton(label: "Apply", onPressed: null),
    );
    await tester.tap(find.text("Apply"), warnIfMissed: false);
    // Nothing to assert beyond the absence of a crash: a disabled primary
    // action must stay inert rather than optimistically succeeding.
    expect(find.text("Apply"), findsOneWidget);
  });

  testWidgets("OutlineGoldButton fires its callback", (
    WidgetTester tester,
  ) async {
    int taps = 0;
    await pumpHarness(
      tester,
      OutlineGoldButton(label: "Pass", onPressed: () => taps++),
    );
    await tester.tap(find.text("Pass"));
    expect(taps, 1);
  });
}
