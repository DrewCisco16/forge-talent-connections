import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/demo_note.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// D5 Veteran pathways.
///
/// A post-MVP concept screen. The fit figures are placeholder concept data, not
/// the output of any model, and the screen says so rather than implying a
/// precision it does not have.
class D5VeteranPathways extends ConsumerWidget {
  const D5VeteranPathways({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: 24),
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: forge.goldGradient),
                borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
              ),
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              child: const Text(
                "VETERAN FIRST",
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.chip,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  color: Colors.white,
                ),
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Text(
            "Your service translates.",
            style: TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: ForgeType.heroTitle,
              fontWeight: FontWeight.bold,
              color: forge.text,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            "What you already did counts as experience. Here is what it maps to.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              height: 1.4,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          ForgeCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const SectionLabel("Your role"),
                const SizedBox(height: 8),
                Text(
                  "0651 · Cyber Network Operator",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.cardTitle,
                    fontWeight: FontWeight.w700,
                    color: forge.gold,
                  ),
                ),
                const SizedBox(height: 14),
                Divider(color: forge.strokeSoft, height: 1),
                const SizedBox(height: 14),
                AsyncView<List<PathwayMatch>>(
                  value: ref.watch(pathwaysProvider),
                  pendingLabel: "Translating your role",
                  builder: (List<PathwayMatch> matches) => Column(
                    children: <Widget>[
                      for (final PathwayMatch m in matches)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Row(
                            children: <Widget>[
                              Expanded(
                                child: Text(
                                  m.role,
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.body,
                                    color: forge.text,
                                  ),
                                ),
                              ),
                              Text(
                                "${m.fitPercent}% fit",
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.caption,
                                  fontWeight: FontWeight.w700,
                                  color: forge.green,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          const BannerNote(
            tone: BannerTone.governance,
            text:
                "These fit figures are concept placeholders, not a real mapping. They will not ship until they come from a source that can be checked.",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          ForgeCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  "Cloud Practitioner Path",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.cardTitle,
                    fontWeight: FontWeight.w700,
                    color: forge.text,
                  ),
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    value: 3 / 8,
                    minHeight: 6,
                    backgroundColor: forge.strokeSoft,
                    valueColor: AlwaysStoppedAnimation<Color>(forge.gold),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  "3 of 8 modules",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    color: forge.textSub,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          GoldButton(
              label: "See My Pathways",
              onPressed: () => demoNote(context,
                  "Pathway matching runs on the backend. These results are "
                  "concept fixtures.")),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
