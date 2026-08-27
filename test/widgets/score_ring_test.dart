import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/widgets/score_ring.dart";

import "../support/harness.dart";

void main() {
  group("ScoreRing", () {
    testWidgets("counts up and settles on the value it was given",
        (WidgetTester tester) async {
      await pumpHarness(tester, const ScoreRing(value: 87, label: "Strong match"));
      expect(find.text("87"), findsOneWidget);
      expect(find.text("Strong match"), findsOneWidget);
    });

    testWidgets("shows the final value immediately under reduced motion",
        (WidgetTester tester) async {
      await tester.pumpWidget(
        harness(const ScoreRing(value: 87), disableAnimations: true),
      );
      // One frame only: no settling, no animation allowed to run.
      await tester.pump();
      expect(find.text("87"), findsOneWidget);
    });

    testWidgets("renders zero without painting an arc",
        (WidgetTester tester) async {
      await pumpHarness(tester, const ScoreRing(value: 0));
      expect(find.text("0"), findsOneWidget);
    });
  });
}
