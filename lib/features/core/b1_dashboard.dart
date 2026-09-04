import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/internal_fire.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/status_chip.dart";

/// B1 Home dashboard.
class B1Dashboard extends ConsumerWidget {
  const B1Dashboard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<UserProfile>(
            value: ref.watch(profileProvider),
            pendingLabel: "Loading your dashboard",
            builder: (UserProfile profile) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                HeroBand(
                  title:
                      "Welcome Back, ${profile.displayName.split(" ").first}",
                  subtitle: "Your collaborations await",
                  trailing: _BellChip(
                    onTap: () => context.go("/notifications"),
                  ),
                ),
                const SizedBox(height: ForgeSpacing.gapSection),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: DemoBadge(),
                ),
                const SizedBox(height: ForgeSpacing.gapCard),
                // Renders only in a build compiled with a live backend
                // address; the pure demo shows nothing here.
                const _LiveBackendBanner(),
                ForgeCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Container(
                            width: 42,
                            height: 42,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: forge.surface2,
                              image: profile.avatarAsset == null
                                  ? null
                                  : DecorationImage(
                                      image: AssetImage(profile.avatarAsset!),
                                      fit: BoxFit.cover,
                                    ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  "Profile Completion ${profile.completionPercent}%",
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.cardTitle,
                                    fontWeight: FontWeight.w700,
                                    color: forge.text,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                // Marketing copy placeholder: do not ship a
                                // number like this without data behind it.
                                Text(
                                  "Verified profiles get more views",
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.caption,
                                    color: forge.textSub,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          StatusChip(
                            status: profile.serviceRecord,
                            dense: true,
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: profile.completionPercent / 100,
                          minHeight: 6,
                          backgroundColor: forge.strokeSoft,
                          valueColor: AlwaysStoppedAnimation<Color>(forge.gold),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // Recognition runs on verified events only: the ladder counts what
          // passed a check, and the streak counts kept commitments - never
          // taps or opens.
          AsyncView<IntegrityStreak>(
            value: ref.watch(streakProvider),
            pendingLabel: "Loading your record",
            builder: (IntegrityStreak streak) {
              final Widget content = Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Icon(
                    streak.active
                        ? Icons.local_fire_department
                        : Icons.local_fire_department_outlined,
                    size: 24,
                    color: streak.active ? forge.gold : forge.textSub,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          streak.label,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.cardTitle,
                            fontWeight: FontWeight.w700,
                            color: forge.text,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          streak.note,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            height: 1.3,
                            color: forge.textSub,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              );
              if (!streak.active) {
                return ForgeCard(borderColor: forge.strokeSoft, child: content);
              }
              // A living streak burns inside its own card bounds; the fire
              // is clipped to the card and goes still under reduced motion.
              return ForgeInternalFireContainer(
                child: Padding(
                  padding: const EdgeInsets.all(ForgeSpacing.cardPad),
                  child: content,
                ),
              );
            },
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // The first thing a new member meets is a person, a real project,
          // and one small contribution they can make this week.
          ForgeCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    const CircleAvatar(
                      radius: 16,
                      backgroundImage: AssetImage("assets/heroes/hero_04.png"),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            "Maya Chen",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.name,
                              fontWeight: FontWeight.bold,
                              color: forge.text,
                            ),
                          ),
                          Text(
                            "Community partner · a person, in person",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              color: forge.textSub,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  "\"Glad you're in, Drew. Start small if you like: the "
                  "seminar outline could use one more review pass this "
                  "week, and the team would love the help.\"",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.body,
                    height: 1.35,
                    color: forge.text,
                  ),
                ),
                const SizedBox(height: 10),
                OutlineGoldButton(
                  label: "Make Your First Contribution",
                  onPressed: () => context.go("/project-space"),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // Rewards run on the same rule as everything else: verified
          // events only. The dashboard row is a teaser; the program screen
          // carries the rules.
          AsyncView<RewardsProgram>(
            value: ref.watch(rewardsProvider),
            pendingLabel: "Loading rewards",
            builder: (RewardsProgram program) => InkWell(
              onTap: () => context.go("/rewards"),
              borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
              child: ForgeCard(
                child: Row(
                  children: <Widget>[
                    Icon(
                      Icons.emoji_events_outlined,
                      size: 22,
                      color: forge.gold,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            "${program.pointsVerified} reward points this "
                            "quarter",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.cardTitle,
                              fontWeight: FontWeight.w700,
                              color: forge.text,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            program.standingNote,
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              height: 1.3,
                              color: forge.textSub,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Icon(Icons.chevron_right, size: 20, color: forge.textSub),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // The assistant and the Proof Builder, one tap away. Both are
          // honest about what runs where: scripted samples in the demo,
          // Google Cloud Vertex AI behind the backend in production.
          InkWell(
            onTap: () => context.go("/assistant"),
            borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
            child: ForgeCard(
              child: Row(
                children: <Widget>[
                  Icon(Icons.smart_toy_outlined, size: 22, color: forge.violet),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          "AI Assistant",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.cardTitle,
                            fontWeight: FontWeight.w700,
                            color: forge.text,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          "Answers, drafting help, and premium scholarly "
                          "research",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            height: 1.3,
                            color: forge.textSub,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, size: 20, color: forge.textSub),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          InkWell(
            onTap: () => context.go("/proof-builder"),
            borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
            child: ForgeCard(
              child: Row(
                children: <Widget>[
                  Icon(
                    Icons.workspace_premium_outlined,
                    size: 22,
                    color: forge.gold,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          "Proof Builder",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.cardTitle,
                            fontWeight: FontWeight.w700,
                            color: forge.text,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          "Your Verified Portfolio, assembled from proof",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            height: 1.3,
                            color: forge.textSub,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, size: 20, color: forge.textSub),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // The two feature previews the founder scheduled for within the
          // year: both are labelled samples in the demo and say so on their
          // own screens.
          InkWell(
            onTap: () => context.go("/talent-stories"),
            borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
            child: ForgeCard(
              child: Row(
                children: <Widget>[
                  Icon(
                    Icons.video_library_outlined,
                    size: 22,
                    color: forge.cyan,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          "Talent Stories",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.cardTitle,
                            fontWeight: FontWeight.w700,
                            color: forge.text,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          "Short verified video introductions, one swipe "
                          "at a time",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            height: 1.3,
                            color: forge.textSub,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, size: 20, color: forge.textSub),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          InkWell(
            onTap: () => context.go("/talent-signature"),
            borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
            child: ForgeCard(
              child: Row(
                children: <Widget>[
                  Icon(Icons.fingerprint, size: 22, color: forge.gold),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          "Talent Signature",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.cardTitle,
                            fontWeight: FontWeight.w700,
                            color: forge.text,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          "Your strengths, drawn only from your verified "
                          "record",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            height: 1.3,
                            color: forge.textSub,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, size: 20, color: forge.textSub),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<TrustWalletSummary>(
            value: ref.watch(walletSummaryProvider),
            pendingLabel: "Loading growth",
            builder: (TrustWalletSummary s) => ForgeCard(
              child: Row(
                children: <Widget>[
                  Expanded(
                    child: _GrowthStat(
                      value: s.deliverables,
                      label: "Verified deliverables",
                    ),
                  ),
                  Expanded(
                    child: _GrowthStat(
                      value: s.credentials,
                      label: "Sealed credentials",
                    ),
                  ),
                  Expanded(
                    child: _GrowthStat(
                      value: s.vouches,
                      label: "Vouches earned",
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Row(
            children: <Widget>[
              Expanded(
                child: GoldButton(
                  label: "Edit Profile",
                  onPressed: () => context.go("/create-profile"),
                ),
              ),
              const SizedBox(width: ForgeSpacing.gapCard),
              Expanded(
                child: OutlineGoldButton(
                  label: "Edit Video Pitch",
                  onPressed: () => context.go("/elevator-pitch"),
                ),
              ),
            ],
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          _WideButton(
            label: "Project Collaborations",
            onTap: () => context.go("/project-space"),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          Row(
            children: <Widget>[
              Expanded(
                child: OutlineGoldButton(
                  label: "Credentials",
                  onPressed: () => context.go("/credentials"),
                ),
              ),
              const SizedBox(width: ForgeSpacing.gapCard),
              Expanded(
                child: OutlineGoldButton(
                  label: "Trust Center",
                  onPressed: () => context.go("/trust-wallet"),
                ),
              ),
            ],
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          ForgeCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        "AI-Suggested Opportunities",
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.cardTitle,
                          fontWeight: FontWeight.w700,
                          color: forge.text,
                        ),
                      ),
                    ),
                    Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(colors: forge.goldGradient),
                        borderRadius: BorderRadius.circular(
                          ForgeShape.pillRadius,
                        ),
                      ),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      child: const Text(
                        "New",
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.chip,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                // Required copy. Ships verbatim.
                Text(
                  "Suggestions only. A person reviews every match.",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    color: forge.textSub,
                  ),
                ),
                const SizedBox(height: ForgeSpacing.gapCard),
                AsyncView<List<Opportunity>>(
                  value: ref.watch(suggestedOpportunitiesProvider),
                  pendingLabel: "Loading suggestions",
                  builder: (List<Opportunity> items) => Column(
                    children: <Widget>[
                      for (final Opportunity o in items)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: InkWell(
                            onTap: () => context.go("/match/${o.id}"),
                            child: Row(
                              children: <Widget>[
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: <Widget>[
                                      Text(
                                        o.title,
                                        style: TextStyle(
                                          fontFamily: ForgeType.bodyFamily,
                                          fontSize: ForgeType.body,
                                          fontWeight: FontWeight.w600,
                                          color: forge.text,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Row(
                                        children: <Widget>[
                                          if (o.organizationStatus ==
                                              VerificationStatus.verified)
                                            Padding(
                                              padding: const EdgeInsets.only(
                                                right: 5,
                                              ),
                                              child: Icon(
                                                Icons.circle,
                                                size: 7,
                                                color: forge.green,
                                              ),
                                            ),
                                          Flexible(
                                            child: Text(
                                              o.organization,
                                              overflow: TextOverflow.ellipsis,
                                              style: TextStyle(
                                                fontFamily:
                                                    ForgeType.bodyFamily,
                                                fontSize: ForgeType.caption,
                                                color: forge.textSub,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                Icon(
                                  Icons.chevron_right,
                                  size: 17,
                                  color: forge.textSub,
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _GrowthStat extends StatelessWidget {
  const _GrowthStat({required this.value, required this.label});

  final int value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Column(
      children: <Widget>[
        GoldGradientText(
          "$value",
          style: const TextStyle(
            fontFamily: ForgeType.displayFamily,
            fontSize: 22,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: ForgeType.bodyFamily,
            fontSize: ForgeType.chip,
            height: 1.25,
            color: forge.textSub,
          ),
        ),
      ],
    );
  }
}

class _BellChip extends StatelessWidget {
  const _BellChip({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return InkWell(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: ForgeColors.navyDeep,
          borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
          border: Border.all(color: forge.strokeSoft),
        ),
        padding: const EdgeInsets.all(8),
        child: Icon(Icons.notifications_none, size: 17, color: forge.gold),
      ),
    );
  }
}

class _WideButton extends StatelessWidget {
  const _WideButton({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: forge.goldDeep,
          borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
        ),
        padding: const EdgeInsets.symmetric(vertical: 14),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontFamily: ForgeType.bodyFamily,
            fontSize: ForgeType.cardTitle,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}

/// The live-connection banner.
///
/// Truthful in all three states: absent entirely when the build carries no
/// backend address (the pure fixture demo), a quiet confirmation when the
/// live edge answers healthy, and a plain fail-closed notice when it does
/// not. It never renders a connected state it has not verified.
class _LiveBackendBanner extends ConsumerWidget {
  const _LiveBackendBanner();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);
    final AsyncValue<bool?> health = ref.watch(backendHealthProvider);

    final bool? healthy = health.whenOrNull(data: (bool? v) => v);
    if (health.hasValue && healthy == null) {
      // No backend configured: this is the fixture demo, show nothing.
      return const SizedBox.shrink();
    }
    if (!health.hasValue && !health.isLoading) {
      return const SizedBox.shrink();
    }
    if (health.isLoading) {
      return const SizedBox.shrink();
    }

    final bool ok = healthy ?? false;
    final Color tone = ok ? forge.gold : forge.violet;
    return Padding(
      padding: const EdgeInsets.only(bottom: ForgeSpacing.gapCard),
      child: Container(
        decoration: BoxDecoration(
          color: tone.withValues(alpha: 0.09),
          border: Border.all(color: tone.withValues(alpha: 0.5)),
          borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: <Widget>[
            Icon(
              ok ? Icons.cloud_done : Icons.cloud_off,
              size: 18,
              color: tone,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                ok
                    ? "Live backend connected"
                    : "Live backend unreachable. Demo data is shown and "
                          "nothing was changed.",
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
      ),
    );
  }
}
