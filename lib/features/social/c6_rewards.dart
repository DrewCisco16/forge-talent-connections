import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/demo_note.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/social_action.dart";
import "../../widgets/status_chip.dart";

/// C6 Rewards and referrals.
///
/// The incentive layer over vouching and referrals, built on the Theory of
/// Planned Behavior: the prize card answers "what's in it for me" (attitude),
/// the community count shows that people like you take part (norm), and the
/// how-to-earn list makes the path concrete and attainable (perceived
/// behavioral control). Every point is awarded by the backend from a verified
/// event; a frozen account shows its freeze, never a payout path.
class C6Rewards extends ConsumerWidget {
  const C6Rewards({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: AsyncView<RewardsProgram>(
        value: ref.watch(rewardsProvider),
        pendingLabel: "Loading rewards",
        builder: (RewardsProgram program) {
          final bool frozen =
              program.status == VerificationStatus.locked;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              const SizedBox(height: ForgeSpacing.gapSection),
              const Align(
                  alignment: Alignment.centerRight, child: DemoBadge()),
              const SizedBox(height: 8),
              const HeroBand(
                title: "Rewards & Referrals",
                subtitle: "Verified effort, rewarded every quarter",
              ),
              const SizedBox(height: ForgeSpacing.gapSection),

              // The person's standing. Fail-closed: a hold shows the freeze
              // and the human-review path, never a payout that might work.
              ForgeCard(
                borderColor: frozen ? forge.red : forge.gold,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            "${program.quarterLabel} points",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.cardTitle,
                              fontWeight: FontWeight.w700,
                              color: forge.text,
                            ),
                          ),
                        ),
                        StatusChip(status: program.status, dense: true),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: <Widget>[
                        Text(
                          "${program.pointsVerified}",
                          style: TextStyle(
                            fontFamily: ForgeType.displayFamily,
                            fontSize: 40,
                            fontWeight: FontWeight.bold,
                            height: 1,
                            color: frozen ? forge.textSub : forge.gold,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.only(bottom: 3),
                            child: Text(
                              program.pointsPending > 0
                                  ? "verified points · "
                                      "${program.pointsPending} pending "
                                      "verification"
                                  : "verified points",
                              style: TextStyle(
                                fontFamily: ForgeType.bodyFamily,
                                fontSize: ForgeType.caption,
                                height: 1.3,
                                color: forge.textSub,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      "${program.standingNote} · quarter ends "
                      "${program.quarterEnds}",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        fontWeight: FontWeight.w600,
                        color: frozen ? forge.red : forge.text,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      program.note,
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

              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("What your points can win"),
              const SizedBox(height: 6),
              Text(
                "Prizes go to the members with the most verified points. "
                "Every award is preceded by a human audit of the points "
                "behind it.",
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.caption,
                  height: 1.35,
                  color: forge.textSub,
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapCard),
              for (final RewardPrize prize in program.quarterlyPrizes)
                Padding(
                  padding:
                      const EdgeInsets.only(bottom: ForgeSpacing.gapCard),
                  child: _PrizeCard(prize: prize, icon: Icons.card_giftcard),
                ),
              _PrizeCard(
                prize: program.yearlyPrize,
                icon: Icons.directions_car_outlined,
                highlighted: true,
              ),

              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("How points are earned"),
              const SizedBox(height: 6),
              Text(
                "Only verified actions earn. Nothing is awarded for taps, "
                "raw activity, or volume alone.",
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.caption,
                  height: 1.35,
                  color: forge.textSub,
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapCard),
              ForgeCard(
                child: Column(
                  children: <Widget>[
                    for (final (String how, String pts) in <(String, String)>[
                      ("A vouch you sign verifies", "+40"),
                      ("Someone you refer joins and verifies", "+100"),
                      ("A deliverable of yours is sealed", "+60"),
                      ("A vouch you signed ages well for a year", "+80"),
                    ])
                      Padding(
                        padding: const EdgeInsets.only(bottom: 9),
                        child: Row(
                          children: <Widget>[
                            Icon(Icons.bolt_outlined,
                                size: 15, color: forge.gold),
                            const SizedBox(width: 9),
                            Expanded(
                              child: Text(
                                how,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.body,
                                  height: 1.3,
                                  color: forge.text,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              pts,
                              style: TextStyle(
                                fontFamily: ForgeType.bodyFamily,
                                fontSize: ForgeType.body,
                                fontWeight: FontWeight.w700,
                                color: forge.gold,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),

              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Bring talented people with you"),
              const SizedBox(height: 6),
              Text(
                "Share your referral code. When someone joins with it and "
                "their verification clears, you both benefit: they arrive "
                "with a trusted introduction, you earn points.",
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.caption,
                  height: 1.35,
                  color: forge.textSub,
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapCard),
              ForgeCard(
                borderColor: forge.violet.withValues(alpha: 0.6),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Icon(Icons.qr_code_2, size: 20, color: forge.gold),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            program.referralCode,
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.cardTitle,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.2,
                              color: forge.text,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      program.referralsPending > 0
                          ? "${program.referralsJoined} joined and verified "
                              "· ${program.referralsPending} still verifying"
                          : "${program.referralsJoined} joined and verified",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        color: forge.textSub,
                      ),
                    ),
                    const SizedBox(height: 10),
                    VibeButton(
                      label: "Share My Code",
                      icon: Icons.ios_share,
                      fullWidth: true,
                      onPressed: () => demoNote(context,
                          "Sharing opens your device's share sheet with "
                          "the backend attached."),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("This quarter's standings"),
              const SizedBox(height: 6),
              Text(
                "${program.membersEarning} members earned points this "
                "quarter. Standings below the top are shown as tiers, so "
                "early progress counts instead of discouraging.",
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.caption,
                  height: 1.35,
                  color: forge.textSub,
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapCard),
              ForgeCard(
                child: Column(
                  children: <Widget>[
                    for (final (int i, LeaderEntry e)
                        in program.topThree.indexed)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          children: <Widget>[
                            SizedBox(
                              width: 22,
                              child: Text(
                                "${i + 1}",
                                style: TextStyle(
                                  fontFamily: ForgeType.displayFamily,
                                  fontSize: ForgeType.cardTitle,
                                  fontWeight: FontWeight.bold,
                                  color: i == 0
                                      ? forge.gold
                                      : forge.textSub,
                                ),
                              ),
                            ),
                            CircleAvatar(
                              radius: 14,
                              backgroundColor: forge.surface2,
                              backgroundImage: AssetImage(e.avatar),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                e.name,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.body,
                                  fontWeight: FontWeight.w600,
                                  color: forge.text,
                                ),
                              ),
                            ),
                            Text(
                              "${e.points} pts",
                              style: TextStyle(
                                fontFamily: ForgeType.bodyFamily,
                                fontSize: ForgeType.caption,
                                fontWeight: FontWeight.w700,
                                color: forge.gold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    Row(
                      children: <Widget>[
                        Icon(Icons.person_outline,
                            size: 15, color: forge.textSub),
                        const SizedBox(width: 9),
                        Expanded(
                          child: Text(
                            "You: ${program.standingNote}",
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
                ),
              ),

              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Your points this quarter"),
              const SizedBox(height: ForgeSpacing.gapCard),
              ForgeCard(
                child: Column(
                  children: <Widget>[
                    for (final RewardEvent e in program.events)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Expanded(
                              child: Column(
                                crossAxisAlignment:
                                    CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text(
                                    e.label,
                                    style: TextStyle(
                                      fontFamily: ForgeType.bodyFamily,
                                      fontSize: ForgeType.body,
                                      height: 1.3,
                                      color: forge.text,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    "${e.when} · +${e.points} pts",
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
                            StatusChip(status: e.status, dense: true),
                          ],
                        ),
                      ),
                  ],
                ),
              ),

              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Fair play — the rules that keep it real"),
              const SizedBox(height: ForgeSpacing.gapCard),
              ForgeCard(
                borderColor: forge.gold.withValues(alpha: 0.55),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    for (final String rule in <String>[
                      "Points must be earned by you, a person — never by a "
                          "company, bot, script, AI agent, purchased "
                          "account, or anyone acting on your behalf.",
                      "One account per person. Pooling, trading, or "
                          "selling points voids them.",
                      "Every prize is preceded by a human audit of the "
                          "points behind it.",
                      "Violations void the prize, forfeit the points, and "
                          "can end membership. Conduct that breaks the law "
                          "— fraud, impersonation, unauthorized automation "
                          "— can be referred to law enforcement.",
                      "No purchase is ever necessary to earn points or "
                          "win. Void where prohibited by law.",
                      "The program is run from Florida under Florida law "
                          "as a competition of verified skill and effort. "
                          "Where a prize period legally requires a state "
                          "filing or a secured prize pool, that is done "
                          "before it starts.",
                    ])
                      Padding(
                        padding: const EdgeInsets.only(bottom: 9),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Icon(Icons.gavel_outlined,
                                size: 14, color: forge.gold),
                            const SizedBox(width: 9),
                            Expanded(
                              child: Text(
                                rule,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.caption,
                                  height: 1.35,
                                  color: forge.text,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    OutlineGoldButton(
                      label: "Read the Full Terms & Privacy",
                      onPressed: () => context.go("/legal"),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapCard),
              const BannerNote(
                tone: BannerTone.governance,
                text: "Draft program rules for demonstration. Final prize "
                    "rules are reviewed by licensed counsel for every place "
                    "the program runs before launch.",
              ),
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }
}

class _PrizeCard extends StatelessWidget {
  const _PrizeCard({
    required this.prize,
    required this.icon,
    this.highlighted = false,
  });

  final RewardPrize prize;
  final IconData icon;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return ForgeCard(
      borderColor: highlighted ? forge.gold : null,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, size: 22, color: forge.gold),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  prize.title,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.cardTitle,
                    fontWeight: FontWeight.w700,
                    color: forge.text,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  prize.detail,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    height: 1.35,
                    color: forge.textSub,
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  prize.valueLabel,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    fontWeight: FontWeight.w700,
                    color: forge.gold,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
