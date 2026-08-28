import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// A5 Elevator pitch.
class A5ElevatorPitch extends ConsumerWidget {
  const A5ElevatorPitch({super.key});

  static String _clock(int seconds) {
    final String s = (seconds % 60).toString().padLeft(2, "0");
    return "${seconds ~/ 60}:$s";
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          HeroBand(
            title: "Elevator Pitch",
            subtitle: "Show your personality in 60 seconds",
            onBack: () => context.go("/veteran-verification"),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<ElevatorPitch>(
            value: ref.watch(elevatorPitchProvider),
            pendingLabel: "Loading your pitch",
            builder: (ElevatorPitch pitch) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Center(
                  child: Container(
                    width: 210,
                    height: 300,
                    decoration: BoxDecoration(
                      color: ForgeColors.navyDeep,
                      borderRadius:
                          BorderRadius.circular(ForgeShape.cardRadius),
                      border: Border.all(color: forge.gold, width: 1.5),
                    ),
                    child: Stack(
                      children: <Widget>[
                        Center(
                          child: Container(
                            width: 54,
                            height: 54,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient:
                                  LinearGradient(colors: forge.goldGradient),
                            ),
                            child: const Icon(Icons.play_arrow,
                                size: 28, color: Colors.white),
                          ),
                        ),
                        Positioned(
                          left: 10,
                          top: 10,
                          child: _Chip(
                            label: pitch.captionsOn ? "CC on" : "CC off",
                          ),
                        ),
                        if (pitch.isAiPresented)
                          const Positioned(
                            right: 10,
                            top: 10,
                            child: AiGeneratedLabel(),
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: ForgeSpacing.gapSection),
                Row(
                  children: <Widget>[
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: LinearGradient(colors: forge.goldGradient),
                      ),
                      child: const Icon(Icons.play_arrow,
                          size: 17, color: Colors.white),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: pitch.positionSeconds / pitch.durationSeconds,
                          minHeight: 5,
                          backgroundColor: forge.strokeSoft,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(forge.gold),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      "${_clock(pitch.positionSeconds)} / ${_clock(pitch.durationSeconds)}",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        color: forge.textSub,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: ForgeSpacing.gapSection),
                Row(
                  children: <Widget>[
                    Expanded(
                      child: GoldButton(label: "Upload Video", onPressed: () {}),
                    ),
                    const SizedBox(width: ForgeSpacing.gapCard),
                    Expanded(
                      child: OutlineGoldButton(
                        label: "Record Video",
                        onPressed: () {},
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const BannerNote(
            tone: BannerTone.coach,
            title: "60-second structure that works",
            text:
                "Who you are 0-10s\nOne verified win with a number 10-35s\nWhat you want next 35-60s",
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          const BannerNote(
            text:
                "Using an AI presenter? It will carry a visible AI-generated label wherever it plays.",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          GoldButton(
            label: "Finish Setup",
            onPressed: () => context.go("/dashboard"),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: ForgeColors.navyDeep.withValues(alpha: 0.8),
        border: Border.all(color: forge.strokeSoft),
        borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      child: Text(
        label,
        style: TextStyle(
          fontFamily: ForgeType.bodyFamily,
          fontSize: ForgeType.chip,
          fontWeight: FontWeight.w700,
          color: forge.text,
        ),
      ),
    );
  }
}
