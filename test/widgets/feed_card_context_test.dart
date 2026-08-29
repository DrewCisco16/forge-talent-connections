import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/feed_card.dart";

/// Feed cards never expose a bare vouch total as a popularity score. The
/// count always ships inside its contextual phrase.
void main() {
  testWidgets("the vouch count renders as context, never a bare number", (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildForgeTheme(),
        home: Scaffold(
          body: FeedCard(
            name: "Maya Chen",
            event: "shipped a verified deliverable",
            body: "Closed out the milestone.",
            vouchCount: 9,
          ),
        ),
      ),
    );
    expect(find.text("Work vouched · 9"), findsOneWidget);
    expect(
      find.text("9"),
      findsNothing,
      reason: "a bare total reads as a ranking",
    );
  });
}
