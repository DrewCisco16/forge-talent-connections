import "dart:math" as math;

import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// A card surface whose forge fire burns strictly inside its own bounds.
///
/// The flame is a symmetric sine-by-cosine wave anchored to the card's
/// bottom edge, painted under the content and clipped to the rounded
/// rectangle, so the effect never bleeds past the widget. A slow perimeter
/// glow sweeps the border. Celebration-grade brand energy for earned
/// states only: the streak that is alive, the points that are verified.
///
/// Reduced motion: the ticker never starts and a single static frame is
/// painted, so the surface stays readable without movement.
class ForgeInternalFireContainer extends StatefulWidget {
  const ForgeInternalFireContainer({
    required this.child,
    this.borderRadius = ForgeShape.cardRadius,
    super.key,
  });

  final Widget child;
  final double borderRadius;

  @override
  State<ForgeInternalFireContainer> createState() =>
      _ForgeInternalFireContainerState();
}

class _ForgeInternalFireContainerState extends State<ForgeInternalFireContainer>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 3),
  );
  bool _decided = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_decided) return;
    _decided = true;
    if (!MediaQuery.disableAnimationsOf(context)) {
      _controller.repeat();
    } else {
      _controller.value = 0.35;
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

    return RepaintBoundary(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) => CustomPaint(
          painter: ForgeInternalFirePainter(
            animationValue: _controller.value,
            borderRadius: widget.borderRadius,
            surface: forge.surface,
            ember: forge.coral,
            flame: forge.gold,
          ),
          child: child,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(widget.borderRadius),
          child: widget.child,
        ),
      ),
    );
  }
}

/// Paints the bounded fire: surface, symmetric wave, perimeter glow.
/// Everything is clipped to the rounded rectangle before a single stroke
/// lands, which is the whole point: the fire lives inside the design.
class ForgeInternalFirePainter extends CustomPainter {
  const ForgeInternalFirePainter({
    required this.animationValue,
    required this.borderRadius,
    required this.surface,
    required this.ember,
    required this.flame,
  });

  final double animationValue;
  final double borderRadius;
  final Color surface;
  final Color ember;
  final Color flame;

  @override
  void paint(Canvas canvas, Size size) {
    final Rect rect = Offset.zero & size;
    final RRect rrect = RRect.fromRectAndRadius(
      rect,
      Radius.circular(borderRadius),
    );

    canvas.save();
    canvas.clipRRect(rrect);

    // The card surface itself, so content sits on the normal ground.
    canvas.drawRect(rect, Paint()..color = surface);

    // Symmetric combustion wave along the bottom edge. Sine against cosine
    // keeps the crest pattern balanced across the width.
    final double waveHeight = size.height * 0.10;
    final double baseHeight = size.height * 0.82;
    final Path firePath = Path()
      ..moveTo(0, size.height)
      ..lineTo(0, baseHeight);
    for (double x = 0; x <= size.width; x += 2) {
      final double s = math.sin(
        (x / size.width * 2 * math.pi) + (animationValue * 2 * math.pi),
      );
      final double c = math.cos(
        (x / size.width * 4 * math.pi) - (animationValue * 2 * math.pi),
      );
      firePath.lineTo(x, baseHeight + s * c * waveHeight);
    }
    firePath
      ..lineTo(size.width, size.height)
      ..close();

    final Paint firePaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.bottomCenter,
        end: Alignment.topCenter,
        colors: <Color>[
          ember.withValues(alpha: 0.38),
          flame.withValues(alpha: 0.26),
          flame.withValues(alpha: 0.0),
        ],
        stops: const <double>[0.0, 0.6, 1.0],
      ).createShader(rect);
    canvas.drawPath(firePath, firePaint);

    // Perimeter heat glow, sweeping slowly around the border.
    final Paint glowPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..shader = LinearGradient(
        colors: <Color>[flame, ember, flame],
        transform: GradientRotation(animationValue * 2 * math.pi),
      ).createShader(rect);
    canvas.drawRRect(rrect.deflate(1), glowPaint);

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant ForgeInternalFirePainter oldDelegate) =>
      oldDelegate.animationValue != animationValue;
}
