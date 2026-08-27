import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// A circular score dial that counts up to its value and settles.
///
/// The score is a suggestion produced by the backend and displayed here. This
/// widget computes nothing: it renders the number it is given.
///
/// Reduced motion: when `MediaQuery.disableAnimations` is set, the ring paints
/// its final value immediately. The count-up is an enhancement, never a
/// precondition for the number being readable.
///
/// The arc gradient defaults to gold. The B6 screen note describes a vibe
/// gradient arc, which conflicts with the rule reserving that gradient for
/// social actions; that conflict is open with Andrew and gold is the
/// conservative default until it is settled.
class ScoreRing extends StatefulWidget {
  const ScoreRing({
    required this.value,
    this.label,
    this.size = 96,
    this.strokeWidth = 8,
    this.duration = const Duration(milliseconds: 900),
    super.key,
  });

  /// The score to display, 0-100, as received from the backend.
  final int value;

  /// A caption under the number, for instance "Strong match".
  final String? label;
  final double size;
  final double strokeWidth;
  final Duration duration;

  @override
  State<ScoreRing> createState() => _ScoreRingState();
}

class _ScoreRingState extends State<ScoreRing>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: widget.duration,
  );

  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Started here rather than in initState so the reduced-motion setting can
    // be read from the inherited MediaQuery.
    if (_started) return;
    _started = true;
    if (MediaQuery.disableAnimationsOf(context)) {
      _controller.value = 1;
    } else {
      _controller.forward();
    }
  }

  @override
  void didUpdateWidget(covariant ScoreRing oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value &&
        !MediaQuery.disableAnimationsOf(context)) {
      _controller.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final double t = Curves.easeOutCubic.transform(_controller.value);
        final int shown = (widget.value * t).round();

        return SizedBox(
          width: widget.size,
          height: widget.size,
          child: CustomPaint(
            painter: _ScoreRingPainter(
              progress: widget.value / 100 * t,
              trackColor: forge.strokeSoft,
              arcColors: forge.goldGradient,
              strokeWidth: widget.strokeWidth,
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    "$shown",
                    style: TextStyle(
                      fontFamily: ForgeType.displayFamily,
                      fontSize: widget.size * 0.29,
                      fontWeight: FontWeight.bold,
                      color: forge.text,
                    ),
                  ),
                  if (widget.label != null)
                    Text(
                      widget.label!,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.chip,
                        color: forge.textSub,
                      ),
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ScoreRingPainter extends CustomPainter {
  const _ScoreRingPainter({
    required this.progress,
    required this.trackColor,
    required this.arcColors,
    required this.strokeWidth,
  });

  final double progress;
  final Color trackColor;
  final List<Color> arcColors;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final Rect rect = Offset.zero & size;
    final Offset center = rect.center;
    final double radius = (size.shortestSide - strokeWidth) / 2;

    final Paint track = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..color = trackColor;
    canvas.drawCircle(center, radius, track);

    if (progress <= 0) return;

    final Paint arc = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        colors: <Color>[...arcColors, arcColors.first],
        startAngle: 0,
        endAngle: 3.141592653589793 * 2,
      ).createShader(rect);

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -3.141592653589793 / 2,
      3.141592653589793 * 2 * progress.clamp(0.0, 1.0),
      false,
      arc,
    );
  }

  @override
  bool shouldRepaint(covariant _ScoreRingPainter old) =>
      old.progress != progress ||
      old.trackColor != trackColor ||
      old.arcColors != arcColors ||
      old.strokeWidth != strokeWidth;
}
