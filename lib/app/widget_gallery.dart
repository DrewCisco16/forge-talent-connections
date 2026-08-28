import "package:flutter/material.dart";

import "../models/verification_status.dart";
import "../theme/forge_theme.dart";
import "../theme/tokens.dart";
import "../widgets/banner_note.dart";
import "../widgets/bottom_nav.dart";
import "../widgets/credential_card.dart";
import "../widgets/feed_card.dart";
import "../widgets/field_box.dart";
import "../widgets/gold_button.dart";
import "../widgets/hero_band.dart";
import "../widgets/phone_scaffold.dart";
import "../widgets/score_ring.dart";
import "../widgets/seal_card.dart";
import "../widgets/social_action.dart";
import "../widgets/status_chip.dart";

/// A gallery of every shared widget in each of its states.
///
/// This is a development surface for reviewing the design system, not a product
/// screen. All strings here are gallery labels or fixtures; none of them are
/// product copy and none assert anything about a real person or credential.
class WidgetGallery extends StatefulWidget {
  const WidgetGallery({super.key});

  @override
  State<WidgetGallery> createState() => _WidgetGalleryState();
}

class _WidgetGalleryState extends State<WidgetGallery> {
  ForgeTab _tab = ForgeTab.home;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    Widget section(String title, List<Widget> children) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const SizedBox(height: ForgeSpacing.gapSection + 6),
            Text(
              title.toUpperCase(),
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: 10,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.1,
                color: forge.gold,
              ),
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            ...children,
          ],
        );

    return PhoneScaffold(
      bottomNav: BottomNav(
        current: _tab,
        onSelected: (ForgeTab t) => setState(() => _tab = t),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          const HeroBand(
            title: "Design System",
            subtitle: "Every shared widget, every state",
          ),

          section("Status chips", <Widget>[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                for (final VerificationStatus s in VerificationStatus.values)
                  StatusChip(status: s),
              ],
            ),
          ]),

          section("Buttons", <Widget>[
            GoldButton(label: "Primary action", onPressed: () {}),
            const SizedBox(height: ForgeSpacing.gapCard),
            const GoldButton(label: "Primary, disabled", onPressed: null),
            const SizedBox(height: ForgeSpacing.gapCard),
            OutlineGoldButton(label: "Secondary action", onPressed: () {}),
          ]),

          section("Social actions (vibe gradient)", <Widget>[
            Row(
              children: <Widget>[
                VibeButton(
                  label: "Vouch",
                  icon: Icons.workspace_premium_outlined,
                  onPressed: () {},
                ),
                const SizedBox(width: 10),
                VibeButton(label: "Share", onPressed: () {}),
              ],
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            Row(
              children: const <Widget>[
                StoryRing(label: "You", image: null, isSelf: true),
                SizedBox(width: 12),
                StoryRing(label: "Maya", image: null),
                SizedBox(width: 12),
                StoryRing(label: "Jordan", image: null),
              ],
            ),
          ]),

          section("Score ring", <Widget>[
            const Row(
              children: <Widget>[
                ScoreRing(value: 87, label: "Strong match"),
                SizedBox(width: 16),
                ScoreRing(value: 42, label: "Partial", size: 78),
              ],
            ),
          ]),

          section("Banners", <Widget>[
            const BannerNote(
              text: "Profiles with a photo and 3+ skills get matched first",
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            const BannerNote(
              tone: BannerTone.governance,
              text:
                  "Your resume only claims what is verified. No invented jobs, dates, or numbers, ever.",
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            const BannerNote(
              tone: BannerTone.denial,
              text:
                  "1 file failed its check and stays locked. If it does not match, it does not go out.",
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            const BannerNote(
              tone: BannerTone.coach,
              title: "60-second structure that works",
              text: "Who you are 0-10s. One verified win 10-35s.",
            ),
          ]),

          section("Fields", <Widget>[
            FieldBox(
              label: "Display name",
              value: "Drew Cisco",
              onHelp: () {},
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            const FieldBox(label: "About", hint: "Tell us about yourself"),
          ]),

          section("Seal card", <Widget>[
            const SealCard(
              title: "Integrity Certificate",
              text:
                  "Once verified, your service record is sealed and tamper-evident. Collaborators see the seal, never your documents.",
              rows: <MapEntry<String, String>>[
                MapEntry("Status", "VERIFIED"),
                MapEntry("Fingerprint", "ab39...e2f1"),
              ],
            ),
          ]),

          section("Credential cards", <Widget>[
            CredentialCard(
              title: "CompTIA Security+ ce",
              status: VerificationStatus.unverified,
              meta: "COMP001022334455 · valid through 2028",
              actionLabel: "Verify Credential",
              onAction: () {},
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            const CredentialCard(
              title: "USMC Service Record",
              status: VerificationStatus.verified,
              meta: "Sealed Aug 2026",
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            const CredentialCard(
              title: "Deliverable bundle",
              status: VerificationStatus.locked,
              meta: "Locked: did not match on last check",
            ),
          ]),

          section("Feed card", <Widget>[
            FeedCard(
              name: "Maya Chen",
              status: VerificationStatus.verified,
              event: "shipped a verified deliverable",
              body:
                  "Closed out the capstone dashboard milestone two days early.",
              vouchCount: 9,
              action: VibeButton(label: "Vouch", onPressed: () {}),
              onMessage: () {},
            ),
          ]),

          const SizedBox(height: ForgeSpacing.gapSection),
          Center(
            child: Text(
              "Tokens $kDesignTokenVersion",
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.caption,
                color: forge.textSub,
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
        ],
      ),
    );
  }
}
