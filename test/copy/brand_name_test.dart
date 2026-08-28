import "dart:io";

import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/onboarding/a1_splash.dart";
import "package:forge_talent_connections/features/social/c1_feed.dart";
import "package:forge_talent_connections/features/trust/d3_sign_in.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// The product name is "FORGE Talent Connections" — the whole name, always.
///
/// Two legal forms exist: the full name inside sentence copy, and the visual
/// lockup, where the wordmark "FORGE" is rendered with "TALENT CONNECTIONS"
/// beside it as a separate styled widget. The static scan enforces the first;
/// the widget tests prove every lockup is complete, so the wordmark never
/// stands alone on a screen.
final RegExp _stringLiteral = RegExp(r'"([^"\\]|\\.)*"');

void main() {
  test("every string naming the product uses the whole name", () {
    final List<String> offences = <String>[];

    for (final FileSystemEntity entity
        in Directory("lib").listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith(".dart")) continue;

      final List<String> lines = entity.readAsLinesSync();
      for (int i = 0; i < lines.length; i++) {
        final String line = lines[i];
        if (line.trimLeft().startsWith("//")) continue;
        for (final RegExpMatch m in _stringLiteral.allMatches(line)) {
          final String literal = m[0]!;
          if (!literal.contains("FORGE")) continue;
          final bool isWordmark = literal == '"FORGE"';
          final bool isFullName = literal.contains("FORGE Talent Connections");
          if (!isWordmark && !isFullName) {
            offences.add("${entity.path}:${i + 1}  $literal");
          }
        }
      }
    }

    expect(
      offences,
      isEmpty,
      reason: 'The product is named "FORGE Talent Connections" in full, or as '
          "the wordmark within a complete lockup. Found:\n"
          "${offences.join("\n")}",
    );
  });

  group("every wordmark lockup is complete", () {
    Future<void> pump(WidgetTester tester, Widget screen) async {
      tester.view.physicalSize = const Size(440, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme: buildForgeTheme(),
            home: MediaQuery(
              data: const MediaQueryData(disableAnimations: true),
              child: screen,
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));
    }

    for (final (String name, Widget screen) in <(String, Widget)>[
      ("A1 Splash", const A1Splash()),
      ("C1 Feed", const C1Feed()),
      ("D3 Sign In", const D3SignIn()),
    ]) {
      testWidgets(name, (WidgetTester tester) async {
        await pump(tester, screen);
        expect(find.text("FORGE"), findsOneWidget,
            reason: "$name shows the wordmark");
        expect(find.text("TALENT CONNECTIONS"), findsOneWidget,
            reason: "$name must complete the lockup — the wordmark never "
                "stands alone");
      });
    }
  });
}
