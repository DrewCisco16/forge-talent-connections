import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

part "social_action.g.dart";

/// Social action surfaces, and the only place the vibe gradient is painted.
///
/// The design tokens reserve the vibe gradient for social actions — vouch,
/// streak, share, and the viewer's own story ring — and bar it from forms and
/// governance banners. That rule is enforced structurally here: the gradient is
/// generated into `social_action.g.dart` as a library-private constant, so no
/// other file in the package can reference it. Adding a new social action means
/// adding it to this library; anything else cannot reach the gradient at all.

/// A social action button: vouch, share, or streak.
class VibeButton extends StatelessWidget {
  const VibeButton({
    required this.label,
    required this.onPressed,
    this.icon,
    this.fullWidth = false,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool fullWidth;

  @override
  Widget build(BuildContext context) {
    final bool enabled = onPressed != null;

    return Opacity(
      opacity: enabled ? 1 : 0.45,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
          child: Ink(
            width: fullWidth ? double.infinity : null,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: _kVibeGradient),
              borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: fullWidth ? MainAxisSize.max : MainAxisSize.min,
                children: <Widget>[
                  if (icon != null) ...<Widget>[
                    Icon(icon, size: 15, color: Colors.white),
                    const SizedBox(width: 7),
                  ],
                  // Flexible so large accessibility text truncates instead
                  // of overflowing the pill.
                  Flexible(
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.body,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A pitch-story avatar ring.
///
/// The viewer's own ring uses the vibe gradient; everyone else's is gold, as
/// specified for the social feed.
class StoryRing extends StatelessWidget {
  const StoryRing({
    required this.label,
    required this.image,
    this.isSelf = false,
    this.size = 62,
    super.key,
  });

  final String label;

  /// Avatar artwork. Null renders the ring around an empty surface, which is
  /// what a story with no loaded image should look like.
  final ImageProvider<Object>? image;

  /// Whether this ring belongs to the viewer, which selects the vibe gradient.
  final bool isSelf;
  final double size;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    const double ringWidth = 3;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              colors: isSelf ? _kVibeGradient : forge.goldGradient,
            ),
          ),
          padding: const EdgeInsets.all(ringWidth),
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: forge.surface,
              image: image == null
                  ? null
                  : DecorationImage(image: image!, fit: BoxFit.cover),
              border: Border.all(color: ForgeColors.navyDeep, width: 2),
            ),
          ),
        ),
        const SizedBox(height: 6),
        SizedBox(
          width: size + 8,
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              color: forge.textSub,
            ),
          ),
        ),
      ],
    );
  }
}

/// The vouch signing control: held, not tapped.
///
/// Signing a vouch attaches a person's name to someone else's work permanently,
/// so it is deliberately harder than a tap. The fill sweeps while held and the
/// signature is only recorded when the sweep completes; lifting early cancels
/// and records nothing.
///
/// Reduced motion: when animations are disabled the control completes on a
/// single press rather than stranding the person behind an animation they
/// cannot see.
class HoldToSignVouch extends StatefulWidget {
  const HoldToSignVouch({
    required this.label,
    required this.onCompleted,
    this.holdDuration = const Duration(milliseconds: 1100),
    super.key,
  });

  final String label;
  final VoidCallback onCompleted;
  final Duration holdDuration;

  @override
  State<HoldToSignVouch> createState() => _HoldToSignVouchState();
}

class _HoldToSignVouchState extends State<HoldToSignVouch>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: widget.holdDuration,
  )..addStatusListener((AnimationStatus status) {
      if (status == AnimationStatus.completed) widget.onCompleted();
    });

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _start() {
    if (MediaQuery.disableAnimationsOf(context)) {
      _controller.value = 1;
      widget.onCompleted();
      return;
    }
    _controller.forward();
  }

  void _cancel() {
    if (!_controller.isCompleted) _controller.reverse();
  }

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return GestureDetector(
      onTapDown: (_) => _start(),
      onTapUp: (_) => _cancel(),
      onTapCancel: _cancel,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          return Container(
            width: double.infinity,
            decoration: BoxDecoration(
              border: Border.all(color: forge.violet, width: 1.5),
              borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
            ),
            clipBehavior: Clip.antiAlias,
            child: Stack(
              children: <Widget>[
                Positioned.fill(
                  child: FractionallySizedBox(
                    alignment: Alignment.centerLeft,
                    widthFactor: _controller.value,
                    child: const DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(colors: _kVibeGradient),
                      ),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: <Widget>[
                      Icon(
                        _controller.isCompleted
                            ? Icons.verified
                            : Icons.touch_app_outlined,
                        size: 16,
                        color: forge.text,
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          _controller.isCompleted
                              ? widget.label
                              : "${widget.label} — hold",
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.center,
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
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
