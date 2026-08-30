import "package:flutter/material.dart";
import "package:video_player/video_player.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";
import "section_label.dart";

/// The pitch video player.
///
/// Plays a bundled video with the app's own controls. Every state is designed
/// rather than improvised: initializing renders a pending state, failure
/// renders an explicit refusal with the reason, and a null asset renders the
/// empty state - the player never pretends a video exists when none does.
///
/// Playback never starts on its own. Autoplay is both a web-policy problem and
/// a reduced-motion problem; the person presses play. Controls carry semantic
/// labels and meet 44pt touch targets.
class PitchVideoPlayer extends StatefulWidget {
  const PitchVideoPlayer({
    required this.videoAsset,
    required this.showAiLabel,
    this.width = 210,
    this.height = 300,
    this.onControllerCreated,
    super.key,
  });

  /// Hands the controller to the caller (for synchronized captions).
  /// The player still owns the controller's lifecycle.
  final ValueChanged<VideoPlayerController>? onControllerCreated;

  /// Bundled asset path, or null for the empty state.
  final String? videoAsset;

  /// Whether the AI-generated label is shown over the surface. Required, not
  /// defaulted: the caller must decide, because forgetting it would remove a
  /// mandatory disclosure.
  final bool showAiLabel;

  final double width;
  final double height;

  @override
  State<PitchVideoPlayer> createState() => _PitchVideoPlayerState();
}

class _PitchVideoPlayerState extends State<PitchVideoPlayer> {
  VideoPlayerController? _controller;

  /// Null while initializing; true when ready; false when initialization
  /// failed. Unknown renders as pending, never as success.
  bool? _ready;
  String? _failureReason;

  @override
  void initState() {
    super.initState();
    final String? asset = widget.videoAsset;
    if (asset == null) {
      _ready = false;
      _failureReason = "No video has been added yet.";
      return;
    }
    final VideoPlayerController controller = VideoPlayerController.asset(asset);
    _controller = controller;
    // Deferred one frame: the player is often created mid-build, and the
    // caller may respond with setState.
    if (widget.onControllerCreated != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) widget.onControllerCreated!.call(controller);
      });
    }
    controller.setLooping(true);
    controller
        .initialize()
        .then((_) {
          if (mounted) setState(() => _ready = true);
        })
        .catchError((Object error) {
          if (mounted) {
            setState(() {
              _ready = false;
              _failureReason = "The video could not be loaded on this device.";
            });
          }
        });
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  void _togglePlay() {
    final VideoPlayerController? controller = _controller;
    if (controller == null || _ready != true) return;
    setState(() {
      controller.value.isPlaying ? controller.pause() : controller.play();
    });
  }

  static String _clock(Duration d) {
    final String s = (d.inSeconds % 60).toString().padLeft(2, "0");
    return "${d.inMinutes}:$s";
  }

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    final VideoPlayerController? controller = _controller;
    final bool playing = controller?.value.isPlaying ?? false;

    // The window takes the video's own aspect ratio once it is known, so the
    // full frame fills it edge to edge: nothing letterboxed, nothing cropped.
    // Until then (pending/error) the design's card proportions hold.
    final double cardWidth = (_ready == true && controller != null)
        ? widget.height * controller.value.aspectRatio
        : widget.width;

    return Column(
      children: <Widget>[
        Center(
          child: Container(
            width: cardWidth,
            height: widget.height,
            decoration: BoxDecoration(
              color: ForgeColors.navyDeep,
              borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
              border: Border.all(color: forge.gold, width: 1.5),
            ),
            clipBehavior: Clip.antiAlias,
            child: Stack(
              alignment: Alignment.center,
              children: <Widget>[
                if (_ready == true && controller != null)
                  // The window already matches the video's aspect, so the
                  // frame fills it exactly on every platform.
                  Positioned.fill(child: VideoPlayer(controller)),
                if (_ready == null)
                  Semantics(
                    label: "Video is loading",
                    child: SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: forge.textSub,
                      ),
                    ),
                  ),
                if (_ready == false)
                  Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: <Widget>[
                        Icon(
                          Icons.videocam_off_outlined,
                          size: 26,
                          color: forge.textSub,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _failureReason ?? "The video could not be loaded.",
                          textAlign: TextAlign.center,
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
                if (_ready == true && !playing)
                  Semantics(
                    button: true,
                    label: "Play video",
                    child: InkWell(
                      onTap: _togglePlay,
                      customBorder: const CircleBorder(),
                      child: Container(
                        width: 54,
                        height: 54,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: LinearGradient(colors: forge.goldGradient),
                        ),
                        child: const Icon(
                          Icons.play_arrow,
                          size: 28,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                if (_ready == true && playing)
                  // The playing surface is one large pause target.
                  Positioned.fill(
                    child: Semantics(
                      button: true,
                      label: "Pause video",
                      child: GestureDetector(
                        onTap: _togglePlay,
                        behavior: HitTestBehavior.opaque,
                        child: const SizedBox.expand(),
                      ),
                    ),
                  ),
                if (widget.showAiLabel)
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
        if (_ready == true && controller != null)
          ValueListenableBuilder<VideoPlayerValue>(
            valueListenable: controller,
            builder: (BuildContext context, VideoPlayerValue value, _) {
              return Row(
                children: <Widget>[
                  Semantics(
                    button: true,
                    label: value.isPlaying ? "Pause" : "Play",
                    child: InkWell(
                      onTap: _togglePlay,
                      customBorder: const CircleBorder(),
                      // 44pt touch target around a 32pt visual control.
                      child: Container(
                        width: 44,
                        height: 44,
                        alignment: Alignment.center,
                        child: Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: LinearGradient(
                              colors: forge.goldGradient,
                            ),
                          ),
                          child: Icon(
                            value.isPlaying ? Icons.pause : Icons.play_arrow,
                            size: 17,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: VideoProgressIndicator(
                      controller,
                      allowScrubbing: true,
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      colors: VideoProgressColors(
                        playedColor: forge.gold,
                        bufferedColor: forge.strokeSoft,
                        backgroundColor: forge.strokeSoft,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    "${_clock(value.position)} / ${_clock(value.duration)}",
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      color: forge.textSub,
                    ),
                  ),
                ],
              );
            },
          ),
      ],
    );
  }
}
