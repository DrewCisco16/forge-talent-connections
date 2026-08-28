import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/gold_button.dart";
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
                  title: "Welcome Back, ${profile.displayName.split(" ").first}",
                  subtitle: "Your collaborations await",
                  trailing: _BellChip(
                    onTap: () => context.go("/notifications"),
                  ),
                ),
                const SizedBox(height: ForgeSpacing.gapSection),
                const Align(alignment: Alignment.centerLeft, child: DemoBadge()),
                const SizedBox(height: ForgeSpacing.gapCard),
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
                          StatusChip(status: profile.serviceRecord, dense: true),
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
                        borderRadius:
                            BorderRadius.circular(ForgeShape.pillRadius),
                      ),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
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
                                                  right: 5),
                                              child: Icon(Icons.circle,
                                                  size: 7, color: forge.green),
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
                                Icon(Icons.chevron_right,
                                    size: 17, color: forge.textSub),
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
