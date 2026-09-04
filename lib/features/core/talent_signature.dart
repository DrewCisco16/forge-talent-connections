import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/status_chip.dart";

/// The Talent Signature: strengths drawn only from the verified record.
///
/// Deliberately not a score. Every strength names the evidence that proves
/// it, evidence still checking renders as still checking, and the feature's
/// refusals are printed on the screen as product copy, because the boundary
/// is part of the feature. In production the signature is drawn by Google
/// Cloud Vertex AI from the verified record, text and sealed work first;
/// reading video or audio waits for consent and legal review.
class TalentSignatureScreen extends ConsumerWidget {
  const TalentSignatureScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          const Align(alignment: Alignment.centerRight, child: DemoBadge()),
          const SizedBox(height: 8),
          const HeroBand(
            title: "Talent Signature",
            subtitle: "Your strengths, drawn only from your verified record",
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<TalentSignature>(
            value: ref.watch(talentSignatureProvider),
            pendingLabel: "Loading your signature",
            builder: (TalentSignature signature) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                ForgeCard(
                  borderColor: forge.gold.withValues(alpha: 0.55),
                  child: Text(
                    signature.summary,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.body,
                      height: 1.5,
                      color: forge.text,
                    ),
                  ),
                ),
                const SizedBox(height: ForgeSpacing.gapSection),
                const SectionLabel("Strengths and their evidence"),
                const SizedBox(height: 6),
                for (final SignatureStrength s
                    in signature.strengths) ...<Widget>[
                  ForgeCard(
                    child: Row(
                      children: <Widget>[
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                s.name,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.cardTitle,
                                  fontWeight: FontWeight.w700,
                                  color: forge.text,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                s.evidence,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.caption,
                                  height: 1.35,
                                  color: forge.textSub,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 10),
                        StatusChip(status: s.status, dense: true),
                      ],
                    ),
                  ),
                  const SizedBox(height: ForgeSpacing.gapCard),
                ],
                const SectionLabel("What this never does"),
                const SizedBox(height: 6),
                ForgeCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      for (final String refusal
                          in signature.refusals) ...<Widget>[
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Icon(Icons.block, size: 14, color: forge.gold),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                refusal,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.caption,
                                  height: 1.4,
                                  color: forge.text,
                                ),
                              ),
                            ),
                          ],
                        ),
                        if (refusal != signature.refusals.last)
                          const SizedBox(height: 8),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Text(
            "In this demo the signature is a labelled sample assembled by "
            "hand from the demo's own records. Within the year, in "
            "production, it is drawn by Google Cloud Vertex AI from your "
            "verified record: text and sealed work first, and reading your "
            "video or audio only with your consent and after legal review. "
            "It is never a score, a ranking, or a guess about who you are, "
            "and it never replaces the two humans behind a vouch.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
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
