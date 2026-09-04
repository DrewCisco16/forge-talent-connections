import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../mock/fixtures.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/brand_lockup.dart";
import "../../widgets/burning_flame.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/operator_footer.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// The Mission and Purpose statement.
///
/// This screen exists to remove ambiguity: it states plainly what FORGE
/// Talent Connections is, what it is not, who it serves, and the human
/// standard everything rests on. It sits in the flow right after the door
/// pages: sign-in continues here, and the role screen continues here, before
/// either lands in the product.
class MissionScreen extends StatelessWidget {
  const MissionScreen({this.next = "/dashboard", super.key});

  /// Where Continue goes: the destination the visitor was headed to.
  final String next;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    Text body(String text) => Text(
      text,
      style: TextStyle(
        fontFamily: ForgeType.bodyFamily,
        fontSize: ForgeType.body,
        height: 1.5,
        color: forge.text,
      ),
    );

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: 28),
          const Center(child: BurningFlame(asset: kFlameMark, height: 72)),
          const SizedBox(height: 8),
          const Center(child: BrandLockup(width: 200)),
          const SizedBox(height: 22),
          Text(
            "Our Mission",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: ForgeType.screenTitle,
              fontWeight: FontWeight.bold,
              color: forge.text,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          ForgeCard(
            borderColor: forge.gold.withValues(alpha: 0.55),
            child: body(
              "FORGE Talent Connections exists for one purpose: to connect "
              "Talent with Opportunity through provable trust. Every "
              "connection here is built on real work, shown as proof, and "
              "vouched for by people who put their own names behind it.",
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("What this is"),
          const SizedBox(height: 6),
          ForgeCard(
            child: body(
              "An invite-only project collaboration network. Talent builds "
              "proof of real work. Trust is earned through human vouches. "
              "Opportunity arrives as scoped projects with confirmed "
              "reviewers, joined by invitation.",
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          const SectionLabel("What this is not"),
          const SizedBox(height: 6),
          ForgeCard(
            child: body(
              "It is not a job board, a feed of listings, or an algorithm "
              "deciding who matters. FORGE Talent Connections complements "
              "LinkedIn and Handshake; it is a different category and "
              "replaces neither.",
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          const SectionLabel("Who it serves"),
          const SizedBox(height: 6),
          ForgeCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                for (final (String role, String line) in <(String, String)>[
                  (
                    "Talent",
                    "People who build. Your work becomes proof that "
                        "travels with you.",
                  ),
                  (
                    "Opportunity",
                    "Sponsors who bring real, scoped projects and stand "
                        "behind their terms.",
                  ),
                  (
                    "Veteran",
                    "Service, sealed and honored, with roads built for "
                        "what comes next.",
                  ),
                ]) ...<Widget>[
                  Text(
                    role,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.cardTitle,
                      fontWeight: FontWeight.w700,
                      color: forge.gold,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    line,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      height: 1.4,
                      color: forge.textSub,
                    ),
                  ),
                  if (role != "Veteran") const SizedBox(height: 10),
                ],
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          const SectionLabel("The standard"),
          const SizedBox(height: 6),
          ForgeCard(
            child: body(
              "Nothing here replaces two humans. An invitation opens the "
              "door and a vouch is earned separately; no credential, "
              "institution, algorithm, seal, patent application, or "
              "recommendation can substitute for either human choice.",
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          const SectionLabel("The road ahead"),
          const SizedBox(height: 6),
          ForgeCard(
            child: body(
              "Within the year: Talent Stories, the Talent Signature, and "
              "AI opportunity matching grow from the samples in this demo "
              "into full features. Within the first year after official "
              "release: exploring Opportunity spaces in augmented reality, "
              "as the content and the technology prove ready.",
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          GoldButton(
            label: "Continue to FORGE Talent Connections",
            onPressed: () => context.go(next),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          const OperatorFooter(),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}
