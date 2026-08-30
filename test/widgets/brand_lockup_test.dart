import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/brand_lockup.dart";

/// The lockup is one even block: FORGE and TALENT CONNECTIONS render at
/// exactly the same width, like the marketing sticker, with the wordmark
/// visually taller at that shared width.
void main() {
  testWidgets("both lines render fitted to one exact width", (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildForgeTheme(),
        home: const Scaffold(body: Center(child: BrandLockup(width: 240))),
      ),
    );

    expect(find.text("FORGE"), findsOneWidget);
    expect(find.text("TALENT CONNECTIONS"), findsOneWidget);

    final Finder fitted = find.byType(FittedBox);
    expect(fitted, findsNWidgets(2));
    final Size wordmark = tester.getSize(fitted.at(0));
    final Size descriptor = tester.getSize(fitted.at(1));
    expect(wordmark.width, 240);
    expect(descriptor.width, 240);
    expect(
      wordmark.height > descriptor.height,
      isTrue,
      reason: "at equal width the wordmark reads larger",
    );
  });
}
