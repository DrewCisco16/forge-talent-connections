import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/models/verification_status.dart";
import "package:forge_talent_connections/widgets/banner_note.dart";
import "package:forge_talent_connections/widgets/bottom_nav.dart";
import "package:forge_talent_connections/widgets/credential_card.dart";
import "package:forge_talent_connections/widgets/feed_card.dart";
import "package:forge_talent_connections/widgets/field_box.dart";
import "package:forge_talent_connections/widgets/gold_button.dart";
import "package:forge_talent_connections/widgets/hero_band.dart";
import "package:forge_talent_connections/widgets/score_ring.dart";
import "package:forge_talent_connections/widgets/seal_card.dart";
import "package:forge_talent_connections/widgets/social_action.dart";
import "package:forge_talent_connections/widgets/status_chip.dart";

import "../support/harness.dart";

/// Golden snapshots for the shared widget set.
///
/// Animations are disabled throughout so a snapshot captures a settled frame
/// rather than a race. Regenerate with:
///   flutter test --update-goldens
void main() {
  Future<void> golden(
    WidgetTester tester,
    String name,
    Widget child, {
    double width = 390,
  }) async {
    await tester.pumpWidget(
      harness(child, width: width, disableAnimations: true),
    );
    await tester.pumpAndSettle();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile("images/$name.png"),
    );
  }

  testWidgets("status chips, all five states", (WidgetTester tester) async {
    await golden(
      tester,
      "status_chips",
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          for (final VerificationStatus s in VerificationStatus.values)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: StatusChip(status: s),
            ),
        ],
      ),
    );
  });

  testWidgets("buttons", (WidgetTester tester) async {
    await golden(
      tester,
      "buttons",
      Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          GoldButton(label: "Apply to Project", onPressed: () {}),
          const SizedBox(height: 10),
          const GoldButton(label: "Disabled", onPressed: null),
          const SizedBox(height: 10),
          OutlineGoldButton(label: "Pass", onPressed: () {}),
        ],
      ),
    );
  });

  testWidgets("social actions carry the vibe gradient", (
    WidgetTester tester,
  ) async {
    await golden(
      tester,
      "social_actions",
      Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              VibeButton(label: "Vouch", onPressed: () {}),
              const SizedBox(width: 10),
              VibeButton(label: "Share", onPressed: () {}),
            ],
          ),
          const SizedBox(height: 16),
          const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              StoryRing(label: "You", image: null, isSelf: true),
              SizedBox(width: 12),
              StoryRing(label: "Maya", image: null),
            ],
          ),
        ],
      ),
    );
  });

  testWidgets("score ring", (WidgetTester tester) async {
    await golden(
      tester,
      "score_ring",
      const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          ScoreRing(value: 87, label: "Strong match"),
          SizedBox(width: 16),
          ScoreRing(value: 42, label: "Partial", size: 78),
        ],
      ),
    );
  });

  testWidgets("banners including the denial tone", (WidgetTester tester) async {
    await golden(
      tester,
      "banners",
      const Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          BannerNote(text: "Verified work and 3+ skills get matched first"),
          SizedBox(height: 10),
          BannerNote(
            tone: BannerTone.governance,
            text: "Your Verified Portfolio only claims what is verified. No invented roles, dates, or numbers, ever.",
          ),
          SizedBox(height: 10),
          BannerNote(
            tone: BannerTone.denial,
            text: "1 file failed its check and stays locked. If it does not match, it does not go out.",
          ),
          SizedBox(height: 10),
          BannerNote(
            tone: BannerTone.coach,
            title: "60-second structure that works",
            text: "Who you are 0-10s. One verified win with a number 10-35s.",
          ),
        ],
      ),
    );
  });

  testWidgets("hero band", (WidgetTester tester) async {
    await golden(
      tester,
      "hero_band",
      HeroBand(
        title: "Veteran Verification",
        subtitle: "Seal your service record so it can be trusted anywhere",
        onBack: () {},
      ),
    );
  });

  testWidgets("field boxes", (WidgetTester tester) async {
    await golden(
      tester,
      "field_boxes",
      Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          FieldBox(label: "Display name", value: "Drew Cisco", onHelp: () {}),
          const SizedBox(height: 10),
          const FieldBox(label: "About", hint: "Tell us about yourself"),
        ],
      ),
    );
  });

  testWidgets("seal card", (WidgetTester tester) async {
    await golden(
      tester,
      "seal_card",
      const SealCard(
        title: "Integrity Certificate",
        text: "Once verified, your service record is sealed and tamper-evident. Collaborators see the seal, never your documents.",
        rows: <MapEntry<String, String>>[
          MapEntry("Status", "VERIFIED"),
          MapEntry("Fingerprint", "ab39...e2f1"),
        ],
      ),
    );
  });

  testWidgets("credential cards across states", (WidgetTester tester) async {
    await golden(
      tester,
      "credential_cards",
      Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          CredentialCard(
            title: "CompTIA Security+ ce",
            status: VerificationStatus.unverified,
            meta: "COMP001022334455 · valid through 2028",
            actionLabel: "Verify Credential",
            onAction: () {},
          ),
          const SizedBox(height: 10),
          const CredentialCard(
            title: "USMC Service Record",
            status: VerificationStatus.verified,
            meta: "Sealed Aug 2026",
          ),
          const SizedBox(height: 10),
          const CredentialCard(
            title: "Deliverable bundle",
            status: VerificationStatus.locked,
            meta: "Locked: did not match on last check",
          ),
        ],
      ),
    );
  });

  testWidgets("feed card", (WidgetTester tester) async {
    await golden(
      tester,
      "feed_card",
      FeedCard(
        name: "Maya Chen",
        status: VerificationStatus.verified,
        event: "shipped a verified deliverable",
        body: "Closed out the capstone dashboard milestone two days early.",
        vouchCount: 9,
        action: VibeButton(label: "Vouch", onPressed: () {}),
        onMessage: () {},
      ),
    );
  });

  testWidgets("bottom nav", (WidgetTester tester) async {
    await golden(
      tester,
      "bottom_nav",
      BottomNav(current: ForgeTab.home, onSelected: (_) {}),
    );
  });
}
