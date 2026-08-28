import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// The technology feature screen: what protects the user, stated as product
/// capability.
///
/// This is the consumer-safe surface for the protected technology portfolio.
/// It describes what each technology does for the person using the app —
/// never how, never under what internal name, and never with claim language.
/// The walled-UI rule still holds: everything described here is enforced by
/// the backend; this screen only presents it.
class TrustTechnology extends StatelessWidget {
  const TrustTechnology({super.key});

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          HeroBand(
            title: "How FORGE Talent Connections Protects You",
            subtitle: "Three technologies underneath every check",
            onBack: () => context.go("/profile"),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              decoration: BoxDecoration(
                color: forge.gold.withValues(alpha: 0.14),
                border: Border.all(color: forge.gold.withValues(alpha: 0.55)),
                borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              child: Text(
                "PATENT-PENDING TECHNOLOGY",
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.chip,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.6,
                  color: forge.gold,
                ),
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          _TechCard(
            icon: Icons.psychology_outlined,
            accent: forge.cyan,
            title: "AI that can't overstep",
            body:
                "Every AI suggestion must clear a confidence bar before it is even considered. Anything uncertain goes to a person instead. A suggestion can never change your record — only verified actions by people do — and every decision is captured in a tamper-evident log.",
            seeItLabel: "See it: AI Match",
            seeItRoute: "/match/employment-law-presentation",
            filing: "US Patent Application Publication 2026/0246640 A1",
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          _TechCard(
            icon: Icons.lock_outline,
            accent: forge.gold,
            title: "A record that can't be quietly changed",
            body:
                "Your verified record is locked by default. A change is staged, checked, and only becomes real once it passes — all at once, or not at all. The full history stays replayable, so what happened can always be shown.",
            seeItLabel: "See it: Trust Wallet",
            seeItRoute: "/trust-wallet",
            filing: "US Patent Application Publication 2026/0186826 A1",
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          _TechCard(
            icon: Icons.verified_outlined,
            accent: forge.green,
            title: "Exports that prove themselves",
            body:
                "Every file receives a standardized fingerprint when it is created. At the moment of export that fingerprint is checked again, and there is only one door out. If it does not match, it does not go out.",
            seeItLabel: "See it: Export",
            seeItRoute: "/export",
            filing: "US Patent Application 19/546,587 (pending)",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Why this matters"),
          const SizedBox(height: ForgeSpacing.gapCard),
          Text(
            "Most platforms ask you to trust what a profile says. FORGE Talent Connections is built so the platform itself cannot lie to you: checks fail closed, denials are shown honestly, and nothing unverified is ever presented as fact.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              height: 1.45,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Text(
            "Patent pending. Applications are published by the USPTO and are "
            "public; publication is not a granted patent.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.chip,
              height: 1.4,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _TechCard extends StatelessWidget {
  const _TechCard({
    required this.icon,
    required this.accent,
    required this.title,
    required this.body,
    required this.seeItLabel,
    required this.seeItRoute,
    this.filing,
  });

  final IconData icon;
  final Color accent;
  final String title;
  final String body;
  final String seeItLabel;
  final String seeItRoute;

  /// The filing this capability is covered by.
  ///
  /// Convention: cite the publication number once an application has published
  /// (it is the citable public record), and the application number while it is
  /// still pending. Null where neither exists — a number is never shown unless
  /// it does.
  final String? filing;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return ForgeCard(
      borderColor: accent.withValues(alpha: 0.5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.13),
                  shape: BoxShape.circle,
                ),
                padding: const EdgeInsets.all(9),
                child: Icon(icon, size: 19, color: accent),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontFamily: ForgeType.displayFamily,
                    fontSize: ForgeType.cardTitle + 1,
                    fontWeight: FontWeight.bold,
                    height: 1.25,
                    color: forge.text,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          Text(
            body,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              height: 1.45,
              color: forge.text,
            ),
          ),
          if (filing != null) ...<Widget>[
            const SizedBox(height: ForgeSpacing.gapCard),
            Container(
              decoration: BoxDecoration(
                color: ForgeColors.navyDeep.withValues(alpha: 0.5),
                border: Border.all(color: forge.strokeSoft),
                borderRadius: BorderRadius.circular(8),
              ),
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              child: Row(
                children: <Widget>[
                  Icon(Icons.description_outlined,
                      size: 12, color: forge.textSub),
                  const SizedBox(width: 7),
                  Flexible(
                    child: Text(
                      filing!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.chip,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.3,
                        color: forge.textSub,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: ForgeSpacing.gapCard),
          InkWell(
            onTap: () => context.go(seeItRoute),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                // Flexible so the link text wraps at large text sizes
                // instead of running past the card edge.
                Flexible(
                  child: Text(
                  seeItLabel,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    fontWeight: FontWeight.w700,
                    color: accent,
                  ),
                  ),
                ),
                const SizedBox(width: 4),
                Icon(Icons.arrow_forward, size: 13, color: accent),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
