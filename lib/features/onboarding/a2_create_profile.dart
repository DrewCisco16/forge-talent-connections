import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../models/models.dart";
import "../../mock/providers.dart";
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
import "../../widgets/status_chip.dart";

/// A2 Create your profile.
class A2CreateProfile extends ConsumerWidget {
  const A2CreateProfile({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          HeroBand(
            title: "Create Your Profile",
            subtitle: "Let's showcase your talents",
            onBack: () => context.go("/"),
            trailing: _NextChip(onTap: () => context.go("/choose-avatar")),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<UserProfile>(
            value: ref.watch(profileProvider),
            pendingLabel: "Loading your profile",
            builder: (UserProfile profile) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                ForgeCard(
                  child: Column(
                    children: <Widget>[
                      _AvatarWithRing(asset: profile.avatarAsset),
                      const SizedBox(height: ForgeSpacing.gapSection),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: GoldButton(
                              label: "Upload Photo",
                              onPressed: () => demoNote(
                                  context,
                                  "Photo upload arrives with the backend. "
                                  "Pick an avatar for now."),
                            ),
                          ),
                          const SizedBox(width: ForgeSpacing.gapCard),
                          Expanded(
                            child: OutlineGoldButton(
                              label: "Choose Avatar",
                              onPressed: () => context.go("/choose-avatar"),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: ForgeSpacing.gapSection),
                FieldBox(
                  label: "Display name",
                  value: profile.displayName,
                  onHelp: () => demoNote(context,
                      "Shown on your profile and inside projects."),
                ),
                const SizedBox(height: ForgeSpacing.gapCard),
                FieldBox(
                  label: "Skills",
                  value: profile.skills.join(", "),
                  onHelp: () => demoNote(context,
                      "How you describe yourself. Verified skills come from "
                      "checked work and live on Credentials."),
                  maxLines: 2,
                ),
                const SizedBox(height: ForgeSpacing.gapCard),
                FieldBox(
                  label: "About",
                  value: profile.about,
                  onHelp: () => demoNote(context,
                      "A short introduction collaborators see first."),
                  maxLines: 3,
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Two ways in"),
          const SizedBox(height: 6),
          Text(
            "Joining takes two vouches — or one vouch plus a sealed "
            "verification, so you can earn your way in on evidence when you "
            "arrive without a network.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.35,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<MembershipStatus>(
            value: ref.watch(membershipProvider),
            pendingLabel: "Checking membership",
            builder: (MembershipStatus m) => ForgeCard(
              borderColor: m.gateOpen ? forge.gold : null,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Icon(
                        m.gateOpen ? Icons.lock_open : Icons.lock_outline,
                        size: 18,
                        color: m.gateOpen ? forge.gold : forge.textSub,
                      ),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Text(
                          m.gateOpen
                              ? "Membership open"
                              : "Membership pending",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.cardTitle,
                            fontWeight: FontWeight.w700,
                            color: forge.text,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: <Widget>[
                      Icon(Icons.how_to_reg,
                          size: 15, color: forge.gold),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Text(
                          "Vouches: ${m.vouchesReceived} of "
                          "${m.vouchesRequired}",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.body,
                            color: forge.text,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 7),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Icon(Icons.verified_outlined,
                          size: 15, color: forge.gold),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Text(
                          m.earnedLaneLabel,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.body,
                            height: 1.3,
                            color: forge.text,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      StatusChip(status: m.earnedLaneStatus, dense: true),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          // Matching leads with contribution evidence, never appearance:
          // prioritising photographs would quietly turn project discovery
          // into a looks-influenced system.
          const BannerNote(
            text: "Verified work and 3+ skills get matched first",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Text(
            "Sample profile data. Nothing here is a verified record.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _NextChip extends StatelessWidget {
  const _NextChip({required this.onTap});

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
        child: Icon(Icons.arrow_forward, size: 17, color: forge.gold),
      ),
    );
  }
}

class _AvatarWithRing extends StatelessWidget {
  const _AvatarWithRing({this.asset});

  final String? asset;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return SizedBox(
      width: 120,
      height: 120,
      child: Stack(
        children: <Widget>[
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(colors: forge.goldGradient),
            ),
            padding: const EdgeInsets.all(4),
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: forge.surface2,
                image: asset == null
                    ? null
                    : DecorationImage(
                        image: AssetImage(asset!), fit: BoxFit.cover),
              ),
            ),
          ),
          Positioned(
            right: 0,
            bottom: 4,
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(colors: forge.goldGradient),
                border: Border.all(color: ForgeColors.navyDeep, width: 2),
              ),
              padding: const EdgeInsets.all(6),
              child: const Icon(Icons.edit, size: 13, color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}
