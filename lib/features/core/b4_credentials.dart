import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../util/linear_search.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/demo_note.dart";
import "../../widgets/credential_card.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/status_chip.dart";

/// B4 Verified credentials.
class B4Credentials extends ConsumerWidget {
  const B4Credentials({super.key});

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
            title: "Verified Credentials",
            subtitle: "Sealed so collaborators can trust them anywhere",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<List<Credential>>(
            value: ref.watch(credentialsProvider),
            pendingLabel: "Loading credentials",
            builder: (List<Credential> credentials) {
              final int verified = credentials
                  .where((Credential c) => c.status.isProven)
                  .length;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  ForgeCard(
                    child: Row(
                      children: <Widget>[
                        Icon(Icons.shield_outlined, size: 26, color: forge.gold),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                "$verified of ${credentials.length} verified",
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.cardTitle,
                                  fontWeight: FontWeight.w700,
                                  color: forge.text,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                "Collaborators see only what the check proved.",
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.caption,
                                  color: forge.textSub,
                                ),
                              ),
                              const SizedBox(height: 2),
                              // Exhaustive by construction: every credential
                              // was examined, so the count can say so.
                              Text(
                                "All ${credentials.length} were examined — "
                                "nothing was skipped.",
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.chip,
                                  fontWeight: FontWeight.w600,
                                  color: forge.gold,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  // The first unverified credential, found by a linear scan;
                  // -1 means every credential already carries its proof.
                  if (indexOfFirst(credentials,
                          (Credential c) => !c.status.isProven) !=
                      -1) ...<Widget>[
                    const SizedBox(height: ForgeSpacing.gapCard),
                    Row(
                      children: <Widget>[
                        Icon(Icons.flag_outlined,
                            size: 14, color: forge.gold),
                        const SizedBox(width: 7),
                        Expanded(
                          child: Text(
                            "Next to verify: "
                            "${credentials[indexOfFirst(credentials, (Credential c) => !c.status.isProven)].title}",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              fontWeight: FontWeight.w600,
                              color: forge.text,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: ForgeSpacing.gapSection),
                  GoldButton(
                    label: "Verify All Credentials",
                    onPressed: () => demoNote(context,
                        "Verification runs on the backend. Switch scenarios "
                        "in Settings to see each outcome."),
                  ),
                  const SizedBox(height: ForgeSpacing.gapSection),
                  for (final Credential c in credentials) ...<Widget>[
                    CredentialCard(
                      title: c.title,
                      status: c.status,
                      meta: c.metaLine,
                      actionLabel: c.status.isProven ? null : "Verify Credential",
                      onAction: c.status.isProven
                          ? null
                          : () => demoNote(context,
                              "Verification runs on the backend. Switch "
                              "scenarios in Settings to see each outcome."),
                    ),
                    const SizedBox(height: ForgeSpacing.gapCard),
                  ],
                ],
              );
            },
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Verified skills"),
          const SizedBox(height: 6),
          Text(
            "Skills here are demonstrated by verified work, not "
            "self-described. Each one names the work that proves it.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.35,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<List<VerifiedSkill>>(
            value: ref.watch(verifiedSkillsProvider),
            pendingLabel: "Loading skills",
            builder: (List<VerifiedSkill> skills) => ForgeCard(
              child: Column(
                children: <Widget>[
                  for (final VerifiedSkill s in skills)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  s.name,
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.body,
                                    fontWeight: FontWeight.w600,
                                    color: forge.text,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  s.source,
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.caption,
                                    color: forge.textSub,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          StatusChip(status: s.status, dense: true),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
