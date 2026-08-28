import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/field_box.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// B3 Resume builder.
///
/// Consumer-safe language only: the checking machinery is described by what it
/// does for the person, never by internal system names.
class B3ResumeBuilder extends ConsumerWidget {
  const B3ResumeBuilder({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          const HeroBand(
            title: "AI Resume Builder",
            subtitle: "Create a professional resume in minutes",
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
          GoldButton(label: "Generate Resume", onPressed: () {}),
          const SizedBox(height: ForgeSpacing.gapSection),
          // Required copy. Ships verbatim.
          const BannerNote(
            text:
                "Every AI draft passes an integrity check before it becomes real. If the check cannot pass, nothing is produced and you are told why.",
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // Required copy. Ships verbatim.
          const BannerNote(
            tone: BannerTone.governance,
            text:
                "Your resume only claims what is verified. No invented jobs, dates, or numbers, ever.",
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
