import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/core/b1_dashboard.dart";
import "package:forge_talent_connections/features/core/b3_proof_builder.dart";
import "package:forge_talent_connections/features/core/b4_credentials.dart";
import "package:forge_talent_connections/features/core/b6_ai_match.dart";
import "package:forge_talent_connections/features/onboarding/a5_elevator_pitch.dart";
import "package:forge_talent_connections/features/trust/d1_export_certificate.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/providers.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

import "screen_catalog.dart";

Future<void> _pump(
  WidgetTester tester,
  Widget screen,
  DemoScenario scenario,
) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: <Override>[
        demoScenarioProvider.overrideWith((Ref ref) => scenario),
      ],
      child: MaterialApp(
        theme: buildForgeTheme(),
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: screen,
        ),
      ),
    ),
  );
  // Let the repository's simulated latency resolve.
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump(const Duration(milliseconds: 400));
}

void main() {
  // The phone frame the designs target. Large enough that nothing is clipped
  // into an overflow during layout.
  const Size surface = Size(430, 1600);

  group("every screen renders in every fixture state", () {
    for (final DemoScenario scenario in DemoScenario.values) {
      for (final MapEntry<String, Widget> entry in screenCatalog.entries) {
        testWidgets("${entry.key} · ${scenario.label}", (
          WidgetTester tester,
        ) async {
          await tester.binding.setSurfaceSize(surface);
          addTearDown(() => tester.binding.setSurfaceSize(null));

          await _pump(tester, entry.value, scenario);

          // The screen built and painted without throwing.
          expect(tester.takeException(), isNull);
        });
      }
    }
  });

  group("fail-closed behaviour across scenarios", () {
    testWidgets(
      "D1 blocks export and states the reason when a file is locked",
      (WidgetTester tester) async {
        await tester.binding.setSurfaceSize(surface);
        addTearDown(() => tester.binding.setSurfaceSize(null));

        await _pump(tester, const D1ExportCertificate(), DemoScenario.denied);

        // The denial is explicit, verbatim, and the action is disabled.
        expect(find.text("Export blocked"), findsWidgets);
        expect(
          find.text(
            "1 file failed its check and stays locked. If it does not match, it does not go out.",
          ),
          findsOneWidget,
        );
        expect(find.text("Export Verified Work"), findsNothing);
      },
    );

    testWidgets("D1 offers the export only when nothing is blocked", (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pump(tester, const D1ExportCertificate(), DemoScenario.verified);

      expect(find.text("Export Verified Work"), findsOneWidget);
      expect(find.textContaining("stays locked"), findsNothing);
    });

    testWidgets("B1 always carries the human-review sub-line", (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      for (final DemoScenario s in DemoScenario.values) {
        await _pump(tester, const B1Dashboard(), s);
        expect(
          find.text("Suggestions only. A person reviews every match."),
          findsOneWidget,
          reason: "the sub-line must be present in the $s scenario too",
        );
      }
    });

    testWidgets("B6 carries the required suggestion copy in every scenario", (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      for (final DemoScenario s in DemoScenario.values) {
        await _pump(
          tester,
          const B6AiMatch(opportunityId: "employment-law-presentation"),
          s,
        );
        expect(
          find.text(
            "Suggested, not decided. A person reviews every match before anything is final.",
          ),
          findsOneWidget,
        );
        expect(
          find.text(
            "It cannot accept, reject, pay, or publish anything. Suggestions never change your record. Only verified actions by people do.",
          ),
          findsOneWidget,
          reason: "the accordion ships expanded with this text",
        );
      }
    });

    testWidgets("B3 ships both governance banners verbatim", (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pump(tester, const B3ProofBuilder(), DemoScenario.verified);

      expect(
        find.text(
          "Every AI draft passes an integrity check before it becomes real. If the check cannot pass, nothing is produced and you are told why.",
        ),
        findsOneWidget,
      );
      expect(
        find.text(
          "Your Verified Portfolio only claims what is verified. No invented roles, dates, or numbers, ever.",
        ),
        findsOneWidget,
      );
    });

    testWidgets("A5 discloses the AI presenter label", (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pump(tester, const A5ElevatorPitch(), DemoScenario.verified);

      expect(
        find.text(
          "Using an AI presenter? It will carry a visible AI-generated label wherever it plays.",
        ),
        findsOneWidget,
      );
      // And the label itself is actually on the player.
      expect(find.text("AI-generated"), findsOneWidget);
    });

    testWidgets("B4 never presents an unverified credential as verified", (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pump(tester, const B4Credentials(), DemoScenario.denied);

      // Nothing in the denied scenario claims to be verified.
      expect(find.text("VERIFIED"), findsNothing);
    });
  });
}
