import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/fixtures.dart";
import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/section_label.dart";
import "../../widgets/social_action.dart";
import "../../widgets/status_chip.dart";

/// C2 Video pitch story player, full bleed.
class C2VideoPitch extends ConsumerStatefulWidget {
  const C2VideoPitch({super.key});

  @override
  ConsumerState<C2VideoPitch> createState() => _C2VideoPitchState();
}

class _C2VideoPitchState extends ConsumerState<C2VideoPitch> {
  int _segment = 0;
  static const int _segments = 3;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Scaffold(
      backgroundColor: ForgeColors.navyDeep,
      body: GestureDetector(
        onTap: () => setState(
          () => _segment = (_segment + 1) % _segments,
        ),
        onVerticalDragEnd: (DragEndDetails d) {
          if ((d.primaryVelocity ?? 0) > 0) context.go("/feed");
        },
        child: SafeArea(
          child: AsyncView<ElevatorPitch>(
            value: ref.watch(elevatorPitchProvider),
            pendingLabel: "Loading pitch",
            builder: (ElevatorPitch pitch) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  const SizedBox(height: 8),
                  Row(
                    children: <Widget>[
                      for (int i = 0; i < _segments; i++)
                        Expanded(
                          child: Container(
                            height: 3,
                            margin: const EdgeInsets.symmetric(horizontal: 2),
                            decoration: BoxDecoration(
                              color: i <= _segment
                                  ? forge.gold
                                  : forge.strokeSoft,
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: <Widget>[
                      Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: LinearGradient(colors: forge.goldGradient),
                        ),
                        padding: const EdgeInsets.all(2),
                        child: Container(
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            image: DecorationImage(
                              image: AssetImage(kDrewAvatar),
                              fit: BoxFit.cover,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Row(
                              children: <Widget>[
                                Flexible(
                                  child: Text(
                                    "Drew · 60-sec pitch",
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontFamily: ForgeType.bodyFamily,
                                      fontSize: ForgeType.body,
                                      fontWeight: FontWeight.w700,
                                      color: forge.text,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 6),
                                const StatusChip(
                                  status: VerificationStatus.verified,
                                  dense: true,
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              "Network Operations · Splunk · Python",
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
                  Expanded(
                    child: Stack(
                      children: <Widget>[
                        Center(
                          child: Icon(
                            Icons.play_circle_outline,
                            size: 60,
                            color: forge.textSub.withValues(alpha: 0.5),
                          ),
                        ),
                        if (pitch.isAiPresented)
                          const Positioned(
                            top: 12,
                            right: 0,
                            child: AiGeneratedLabel(),
                          ),
                        Positioned(
                          right: 0,
                          bottom: 90,
                          child: Column(
                            children: <Widget>[
                              VibeButton(
                                label: "Vouch",
                                onPressed: () => context.go("/vouch"),
                              ),
                              const SizedBox(height: 14),
                              Icon(Icons.favorite_border,
                                  size: 22, color: forge.text),
                              Text(
                                "214",
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.caption,
                                  color: forge.textSub,
                                ),
                              ),
                              const SizedBox(height: 14),
                              Icon(Icons.ios_share,
                                  size: 20, color: forge.text),
                            ],
                          ),
                        ),
                        if (pitch.captionsOn && pitch.transcript != null)
                          Positioned(
                            left: 0,
                            right: 70,
                            bottom: 44,
                            child: Container(
                              decoration: BoxDecoration(
                                color: ForgeColors.navyDeep
                                    .withValues(alpha: 0.75),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              padding: const EdgeInsets.all(9),
                              child: Text(
                                "CC ${pitch.transcript}",
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.caption,
                                  color: forge.text,
                                ),
                              ),
                            ),
                          ),
                        Positioned(
                          left: 0,
                          bottom: 12,
                          child: Row(
                            children: <Widget>[
                              for (final String tag in <String>[
                                "#SkillsFirst",
                                "#VetToTech",
                                "#Splunk",
                              ])
                                Padding(
                                  padding: const EdgeInsets.only(right: 8),
                                  child: Text(
                                    tag,
                                    style: TextStyle(
                                      fontFamily: ForgeType.bodyFamily,
                                      fontSize: ForgeType.caption,
                                      fontWeight: FontWeight.w600,
                                      color: forge.cyan,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: GoldButton(label: "Re-record", onPressed: () {}),
                      ),
                      const SizedBox(width: ForgeSpacing.gapCard),
                      Expanded(
                        child: OutlineGoldButton(
                          label: "Use This Take",
                          onPressed: () => context.go("/feed"),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
