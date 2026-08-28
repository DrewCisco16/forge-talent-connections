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
import "../../widgets/pitch_video_player.dart";

/// A5 Elevator pitch.
class A5ElevatorPitch extends ConsumerWidget {
  const A5ElevatorPitch({super.key});

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
                // Andrew's marketing advertisement, made with AI inside the
                // product; the visible AI-generated label is mandatory.
                PitchVideoPlayer(
                  videoAsset: pitch.videoAsset,
                  showAiLabel: pitch.isAiPresented,
                ),
                const SizedBox(height: 6),
                Text(
                  "Marketing advertisement · made in FORGE Talent Connections",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    color: forge.textSub,
                  ),
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

