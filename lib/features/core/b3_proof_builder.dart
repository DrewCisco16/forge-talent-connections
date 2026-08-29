import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/demo_note.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/field_box.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// B3 Proof Builder: the Verified Portfolio, assembled from proof.
///
/// Consumer-safe language only: the checking machinery is described by what it
/// does for the person, never by internal system names.
class B3ProofBuilder extends ConsumerWidget {
  const B3ProofBuilder({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          const HeroBand(
            title: "Proof Builder",
            subtitle: "Your Verified Portfolio, assembled from proof",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<UserProfile>(
            value: ref.watch(profileProvider),
            pendingLabel: "Loading your facts",
            builder: (UserProfile profile) => ForgeCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    "Tell us about yourself",
                    style: TextStyle(
                      fontFamily: ForgeType.displayFamily,
                      fontSize: 19,
                      fontWeight: FontWeight.bold,
                      color: forge.gold,
                    ),
                  ),
                  const SizedBox(height: ForgeSpacing.gapCard),
                  FieldBox(
                    label: "Skills",
                    value: profile.skills.join(", "),
                    maxLines: 2,
                  ),
                  const SizedBox(height: ForgeSpacing.gapCard),
                  FieldBox(label: "Bio", value: profile.about, maxLines: 3),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          const SectionLabel("Build from verified facts"),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<TrustWalletSummary>(
            value: ref.watch(walletSummaryProvider),
            pendingLabel: "Counting verified facts",
            builder: (TrustWalletSummary s) => Column(
              children: <Widget>[
                _FactRow(text: "Verified credentials (${s.credentials})"),
                _FactRow(text: "Verified deliverables (${s.deliverables})"),
                const _FactRow(text: "Sealed service record"),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          GoldButton(
            label: "Assemble Verified Portfolio",
            onPressed: () => demoNote(
              context,
              "The assistant's draft below is built from your verified "
              "record.",
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          const SectionLabel("Assistant draft"),
          const SizedBox(height: 6),
          Text(
            "Every line the assistant writes shows the verified record it "
            "rests on. It cannot invent a role, a date, or a number, because "
            "it only writes from what passed a check. In production the "
            "drafting runs on Google Cloud Vertex AI, always behind the "
            "integrity check.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.35,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<AssistantDraft>(
            value: ref.watch(portfolioDraftProvider),
            pendingLabel: "Drafting from your verified record",
            builder: (AssistantDraft draft) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                ForgeCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      for (final DraftLine line in draft.lines)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                line.text,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.body,
                                  height: 1.35,
                                  color: forge.text,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Icon(
                                    Icons.verified_outlined,
                                    size: 13,
                                    color: forge.gold,
                                  ),
                                  const SizedBox(width: 5),
                                  Expanded(
                                    child: Text(
                                      line.sourceLabel,
                                      style: TextStyle(
                                        fontFamily: ForgeType.bodyFamily,
                                        fontSize: ForgeType.chip,
                                        fontWeight: FontWeight.w600,
                                        color: forge.gold,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
                for (final DeclinedClaim d in draft.declined) ...<Widget>[
                  const SizedBox(height: ForgeSpacing.gapCard),
                  ForgeCard(
                    borderColor: forge.strokeSoft,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            Icon(
                              Icons.do_not_disturb_on_outlined,
                              size: 15,
                              color: forge.textSub,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                "Declined to claim ${d.claim}",
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.body,
                                  fontWeight: FontWeight.w600,
                                  color: forge.text,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 5),
                        Text(
                          d.reason,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            height: 1.35,
                            color: forge.textSub,
                          ),
                        ),
                        const SizedBox(height: 10),
                        OutlineGoldButton(
                          label: "Request Human Review",
                          onPressed: () => demoNote(
                            context,
                            "Request recorded. A person will review this "
                            "decision.",
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          // Required copy. Ships verbatim.
          const BannerNote(
            text: "Every AI draft passes an integrity check before it becomes real. If the check cannot pass, nothing is produced and you are told why.",
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // Required copy. Ships verbatim.
          const BannerNote(
            tone: BannerTone.governance,
            text: "Your Verified Portfolio only claims what is verified. No invented roles, dates, or numbers, ever.",
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _FactRow extends StatelessWidget {
  const _FactRow({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: Row(
        children: <Widget>[
          Icon(Icons.check_circle, size: 15, color: forge.gold),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.body,
                color: forge.text,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
