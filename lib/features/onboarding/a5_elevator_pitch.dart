import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/demo_note.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/confidence_meter.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/status_chip.dart";
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
                      child: GoldButton(
                        label: "Upload Video",
                        onPressed: () => demoNote(
                          context,
                          "Video upload arrives with the backend.",
                        ),
                      ),
                    ),
                    const SizedBox(width: ForgeSpacing.gapCard),
                    Expanded(
                      child: OutlineGoldButton(
                        label: "Record Video",
                        onPressed: () => context.go("/video-pitch"),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Create your pitch with AI"),
          const SizedBox(height: 6),
          Text(
            "Generate an AI video pitch of yourself, drafted from your "
            "verified profile. On an app built on verifying who people are, "
            "a likeness is only generated when the backend is at least "
            "95% confident it is really you - below the line, nothing is "
            "produced and you are told why.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.35,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<PitchStudio>(
            value: ref.watch(pitchStudioProvider),
            pendingLabel: "Checking the studio",
            builder: (PitchStudio studio) {
              final bool cleared = studio.status == VerificationStatus.verified;
              return ForgeCard(
                borderColor: cleared ? forge.gold : forge.strokeSoft,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Icon(Icons.auto_awesome, size: 17, color: forge.gold),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            "AI Pitch Studio",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.cardTitle,
                              fontWeight: FontWeight.w700,
                              color: forge.text,
                            ),
                          ),
                        ),
                        StatusChip(status: studio.status, dense: true),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: <Widget>[
                        Icon(
                          studio.consentOnFile
                              ? Icons.check_circle
                              : Icons.radio_button_unchecked,
                          size: 14,
                          color: forge.gold,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            "Likeness consent on file",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              color: forge.text,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: <Widget>[
                        Icon(
                          Icons.face_retouching_natural,
                          size: 14,
                          color: forge.gold,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            studio.likenessConfidencePercent == 0
                                ? "Likeness confidence: checking · "
                                      "${studio.requiredConfidencePercent} "
                                      "required"
                                : "Likeness confidence: "
                                      "${studio.likenessConfidencePercent} of "
                                      "${studio.requiredConfidencePercent} "
                                      "required",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              color: forge.text,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    // The reported confidence against the required line,
                    // visible at a glance. A miss shows the shortfall; it
                    // is never dressed up as a pass.
                    ConfidenceMeter(
                      value: studio.likenessConfidencePercent,
                      required_: studio.requiredConfidencePercent,
                      pending: studio.status == VerificationStatus.pending,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      studio.note,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        height: 1.35,
                        color: cleared ? forge.textSub : forge.text,
                      ),
                    ),
                    const SizedBox(height: 12),
                    GoldButton(
                      label: cleared
                          ? "Generate My AI Pitch"
                          : "Generation locked",
                      // Fail-closed: below the confidence line, or while the
                      // check runs, there is no action that could appear to
                      // succeed.
                      onPressed: cleared
                          ? () => demoNote(
                              context,
                              "Generation runs on the backend's AI video "
                              "partner and returns here with the "
                              "AI-generated label.",
                            )
                          : null,
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const BannerNote(
            tone: BannerTone.coach,
            title: "60-second structure that works",
            text: "Who you are 0-10s\nOne verified win with a number 10-35s\nWhat you want next 35-60s",
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          const BannerNote(
            text: "Using an AI presenter? It will carry a visible AI-generated label wherever it plays.",
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
