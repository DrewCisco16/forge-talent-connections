import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";

import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/ai_output_review.dart";

import "../support/harness.dart";

void main() {
  testWidgets(
    "the review shows all eight checks and ends on the two-human rule",
    (WidgetTester tester) async {
      await pumpHarness(
        tester,
        const SingleChildScrollView(
          child: AiOutputReview(subject: "this suggestion"),
        ),
      );

      expect(find.text("Before You Use This"), findsOneWidget);
      expect(
        find.text(
          "Eight checks a person runs before acting on this suggestion.",
        ),
        findsOneWidget,
      );
      expect(AiOutputReview.checks.length, 8);
      for (final (String letter, String label, String line)
          in AiOutputReview.checks) {
        expect(find.text(letter), findsWidgets);
        expect(find.textContaining("$label. "), findsOneWidget);
        expect(find.textContaining(line), findsOneWidget);
      }
      expect(
        AiOutputReview.checks.last.$3,
        "A suggestion only. Two humans decide.",
      );
    },
  );

  testWidgets("the letters spell the review's own name", (
    WidgetTester tester,
  ) async {
    final String word = AiOutputReview.checks
        .map(((String, String, String) c) => c.$1)
        .join();
    expect(word, "AICRITQU");
  });

  testWidgets("every check line is free of promises and percentages", (
    WidgetTester tester,
  ) async {
    for (final (String _, String label, String line) in AiOutputReview.checks) {
      expect(line.contains("%"), isFalse, reason: label);
      expect(line.toLowerCase().contains("guarantee"), isFalse, reason: label);
    }
    expect(ForgeTheme, isNotNull);
  });
}
