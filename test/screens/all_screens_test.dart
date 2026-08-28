import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/core/b1_dashboard.dart";
import "package:forge_talent_connections/features/core/b2_find_opportunities.dart";
import "package:forge_talent_connections/features/core/b3_resume_builder.dart";
import "package:forge_talent_connections/features/core/b4_credentials.dart";
import "package:forge_talent_connections/features/core/b5_trust_wallet.dart";
import "package:forge_talent_connections/features/core/b6_ai_match.dart";
import "package:forge_talent_connections/features/core/b7_opportunity_detail.dart";
import "package:forge_talent_connections/features/onboarding/a1_splash.dart";
import "package:forge_talent_connections/features/onboarding/a2_create_profile.dart";
import "package:forge_talent_connections/features/onboarding/a3_choose_avatar.dart";
import "package:forge_talent_connections/features/onboarding/a4_veteran_verification.dart";
import "package:forge_talent_connections/features/onboarding/a5_elevator_pitch.dart";
import "package:forge_talent_connections/features/social/c1_feed.dart";
import "package:forge_talent_connections/features/social/c2_video_pitch.dart";
import "package:forge_talent_connections/features/social/c3_vouch_flow.dart";
import "package:forge_talent_connections/features/social/c4_chat.dart";
import "package:forge_talent_connections/features/social/c5_notifications.dart";
import "package:forge_talent_connections/features/trust/d1_export_certificate.dart";
import "package:forge_talent_connections/features/trust/d2_project_space.dart";
import "package:forge_talent_connections/features/trust/d3_sign_in.dart";
import "package:forge_talent_connections/features/trust/d4_profile_settings.dart";
import "package:forge_talent_connections/features/trust/d5_veteran_pathways.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/providers.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// Every screen in the application, by its specification label.
final Map<String, Widget> _screens = <String, Widget>{
  "A1 Splash": const A1Splash(),
  "A2 Create Profile": const A2CreateProfile(),
  "A3 Choose Avatar": const A3ChooseAvatar(),
  "A4 Veteran Verification": const A4VeteranVerification(),
  "A5 Elevator Pitch": const A5ElevatorPitch(),
  "B1 Dashboard": const B1Dashboard(),
  "B2 Find Opportunities": const B2FindOpportunities(),
  "B3 Resume Builder": const B3ResumeBuilder(),
  "B4 Credentials": const B4Credentials(),
  "B5 Trust Wallet": const B5TrustWallet(),
  "B6 AI Match": const B6AiMatch(opportunityId: "atlas-telemetry"),
  "B7 Opportunity Detail":
      const B7OpportunityDetail(opportunityId: "atlas-telemetry"),
  "C1 Feed": const C1Feed(),
  "C2 Video Pitch": const C2VideoPitch(),
  "C3 Vouch Flow": const C3VouchFlow(),
  "C4 Chat": const C4Chat(),
  "C5 Notifications": const C5Notifications(),
  "D1 Export Certificate": const D1ExportCertificate(),
  "D2 Project Space": const D2ProjectSpace(),
  "D3 Sign In": const D3SignIn(),
  "D4 Profile Settings": const D4ProfileSettings(),
  "D5 Veteran Pathways": const D5VeteranPathways(),
};

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
      for (final MapEntry<String, Widget> entry in _screens.entries) {
        testWidgets("${entry.key} · ${scenario.label}",
            (WidgetTester tester) async {
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
    testWidgets("D1 blocks export and states the reason when a file is locked",
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
    });

    testWidgets("D1 offers the export only when nothing is blocked",
        (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pump(tester, const D1ExportCertificate(), DemoScenario.verified);

      expect(find.text("Export Verified Work"), findsOneWidget);
      expect(find.textContaining("stays locked"), findsNothing);
    });

    testWidgets("B1 always carries the human-review sub-line",
        (WidgetTester tester) async {
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

    testWidgets("B6 carries the required suggestion copy in every scenario",
        (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      for (final DemoScenario s in DemoScenario.values) {
        await _pump(
          tester,
          const B6AiMatch(opportunityId: "atlas-telemetry"),
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

    testWidgets("B3 ships both governance banners verbatim",
        (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pump(tester, const B3ResumeBuilder(), DemoScenario.verified);

      expect(
        find.text(
          "Every AI draft passes an integrity check before it becomes real. If the check cannot pass, nothing is produced and you are told why.",
        ),
        findsOneWidget,
      );
      expect(
        find.text(
          "Your resume only claims what is verified. No invented jobs, dates, or numbers, ever.",
        ),
        findsOneWidget,
      );
    });

    testWidgets("A5 discloses the AI presenter label",
        (WidgetTester tester) async {
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

    testWidgets("B4 never presents an unverified credential as verified",
        (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(surface);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await _pump(tester, const B4Credentials(), DemoScenario.denied);

      // Nothing in the denied scenario claims to be verified.
      expect(find.text("VERIFIED"), findsNothing);
    });
  });
}
