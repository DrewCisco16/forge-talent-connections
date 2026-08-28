import "dart:math" as math;

import "package:flutter/material.dart";

import "../theme/forge_theme.dart";

/// The burning flame: the original mark, with fire waving behind it.
///
/// The logo itself is never transformed — no pulsing, no scaling. The burn is
/// a bed of flame tongues drawn behind the mark, each waving on its own phase
/// and frequency so they lick upward organically rather than throbbing in
/// unison, plus rising embers and a breathing ground glow. The mark sits in
/// front, so the fire reads as burning behind the logo.
///
/// The fire is shaped to the logo: the whole widget is exactly the mark's
/// bounding box, the painter is hard-clipped to it, and tongue heights are
/// clamped inside it — so the burn never spills past the top or bottom of
/// the design.
///
/// Reduced motion: when `MediaQuery.disableAnimations` is set, no controller
/// runs and the static mark renders with a fixed soft glow — no fire is drawn,
/// because a frozen frame of flames reads as a smudge, not a burn.
class BurningFlame extends StatefulWidget {
  /// Aspect ratio of assets/brand/forge_flame.png (578 x 780). The widget's
  /// footprint is exactly the mark's box, so the fire cannot escape it.
  static const double logoAspect = 578 / 780;

  const BurningFlame({
    required this.asset,
    this.height = 132,
    super.key,
  });

  final String asset;

  /// Height of the flame artwork itself; the fire draws in a margin around it.
  final double height;

  @override
  State<BurningFlame> createState() => _BurningFlameState();
}

class _BurningFlameState extends State<BurningFlame>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    // One full cycle. Every wave frequency is an integer number of cycles per
    // loop, so the burn has no visible seam when it repeats.
    duration: const Duration(milliseconds: 2400),
  );

  late final List<_Tongue> _tongues;
  late final List<_Ember> _embers;
  bool _started = false;

  @override
  void initState() {
    super.initState();
    // Fixed seed: the fire looks alive but renders deterministically.
    final math.Random random = math.Random(7);
    _tongues = List<_Tongue>.generate(9, (int i) => _Tongue(random, i, 9));
    _embers = List<_Ember>.generate(30, (_) => _Ember(random));
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    if (!MediaQuery.disableAnimationsOf(context)) {
      _controller.repeat();
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
    final double h = widget.height;

    return SizedBox(
      width: h * BurningFlame.logoAspect,
      height: h,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          return Stack(
            fit: StackFit.expand,
            children: <Widget>[
              // The fire — glow, waving tongues, embers — hard-clipped to the
              // mark's own box so the burn never spills past the design.
              ClipRect(
                child: CustomPaint(
                  painter: _FirePainter(
                    tongues: _tongues,
                    embers: _embers,
                    t: _controller.value,
                    animating: _controller.isAnimating,
                    colors: forge.goldGradient,
                  ),
                ),
              ),
              // The original mark, in front, untouched: no transform, ever.
              Image.asset(
                widget.asset,
                fit: BoxFit.contain,
                semanticLabel: "FORGE Talent Connections flame",
              ),
            ],
          );
        },
      ),
    );
  }
}

/// One flame tongue's fixed characteristics; its wave rides the shared clock.
class _Tongue {
  _Tongue(math.Random random, int index, int count)
      // Spread across the base with slight jitter; outer tongues sit lower.
      : lane = (index / (count - 1)) * 2 - 1,
        // Integer cycles per loop keep the repeat seamless.
        riseFreq = 1 + random.nextInt(3),
        swayFreq = 1 + random.nextInt(2),
        risePhase = random.nextDouble(),
        swayPhase = random.nextDouble(),
        width = 0.10 + random.nextDouble() * 0.08,
        height = 0.5 + random.nextDouble() * 0.45;

  /// Horizontal position, -1..1 across the fire bed.
  final double lane;
  final int riseFreq;
  final int swayFreq;
  final double risePhase;
  final double swayPhase;

  /// Base width and nominal height, as fractions of the stage.
  final double width;
  final double height;
}

/// One ember's fixed characteristics.
class _Ember {
  _Ember(math.Random random)
      : phase = random.nextDouble(),
        lane = random.nextDouble() * 2 - 1,
        speed = 0.6 + random.nextDouble() * 0.8,
        size = 1.4 + random.nextDouble() * 2.2,
        sway = 0.5 + random.nextDouble() * 1.5;

  final double phase;
  final double lane;
  final double speed;
  final double size;
  final double sway;
}

class _FirePainter extends CustomPainter {
  const _FirePainter({
    required this.tongues,
    required this.embers,
    required this.t,
    required this.animating,
    required this.colors,
  });

  final List<_Tongue> tongues;
  final List<_Ember> embers;
  final double t;
  final bool animating;
  final List<Color> colors;

  @override
  void paint(Canvas canvas, Size size) {
    final double cx = size.width / 2;
    // The bed sits just above the box bottom so tongue-base blur fades out
    // before the clip instead of being cut to a straight line.
    final double base = size.height * 0.94;
    final double breathe =
        animating ? 0.5 + 0.5 * math.sin(t * 2 * math.pi) : 0.5;

    // Ground glow: the heat under the burn, breathing (fixed at rest). Kept
    // narrow enough that its blur fades out before the clip edges, so no
    // straight clipped line ever shows.
    final Paint glowPaint = Paint()
      ..color = colors.first.withValues(alpha: 0.14 + 0.10 * breathe)
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, size.height * 0.045);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(cx, size.height * 0.87),
        width: size.width * 0.58,
        height: size.height * 0.13,
      ),
      glowPaint,
    );

    // At rest (reduced motion) no fire is drawn — only the soft glow above.
    if (!animating) return;

    // Two passes of tongues: a deep, dim layer and a bright, tighter layer in
    // front of it, both still behind the mark. Each tongue waves on its own
    // frequencies, so the bed licks and leans rather than pulsing as one.
    for (final (double scale, double alpha, Color color, double blur)
        in <(double, double, Color, double)>[
      (1.05, 0.34, colors.last, 5),
      (0.85, 0.50, colors.first, 4),
    ]) {
      final Paint paint = Paint()
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, blur);

      for (final _Tongue tongue in tongues) {
        final double rise = math.sin(
            2 * math.pi * (tongue.riseFreq * t + tongue.risePhase));
        final double sway = math.sin(
            2 * math.pi * (tongue.swayFreq * t + tongue.swayPhase));

        // Outer tongues are shorter, so the bed silhouettes like a fire.
        // Heights are clamped so every tip stays inside the logo's box.
        final double edgeFalloff = 1 - 0.55 * tongue.lane.abs();
        final double tongueHeight = (size.height *
                tongue.height *
                scale *
                edgeFalloff *
                (0.78 + 0.22 * rise))
            .clamp(0.0, base * 0.92);
        final double halfWidth = size.width * tongue.width * scale / 2;
        // Lanes span less than the half-width so flanks, sway, and blur all
        // fade out before the clip edges — no straight cut lines.
        final double x = cx + tongue.lane * size.width * 0.24;
        final double tipX = x + sway * halfWidth * 1.6;
        final double tipY = base - tongueHeight;

        final Path path = Path()
          ..moveTo(x - halfWidth, base)
          // Left flank bows outward low and pulls in toward the waving tip.
          ..quadraticBezierTo(
              x - halfWidth * 1.15,
              base - tongueHeight * 0.45,
              tipX,
              tipY)
          // Right flank mirrors back down to the bed.
          ..quadraticBezierTo(
              x + halfWidth * 1.15,
              base - tongueHeight * 0.45,
              x + halfWidth,
              base)
          ..close();

        paint.color =
            color.withValues(alpha: alpha * (0.8 + 0.2 * rise.abs()));
        canvas.drawPath(path, paint);
      }
    }

    // Embers drifting up out of the bed.
    final Paint emberPaint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.5);
    for (final _Ember ember in embers) {
      final double p = (t * ember.speed + ember.phase) % 1.0;
      final double x = cx +
          ember.lane * size.width * 0.26 +
          math.sin(p * ember.sway * 2 * math.pi + ember.phase * 6) *
              size.width *
              0.05 *
              p;
      final double y = base - p * size.height * 0.85;
      final double fade = (1 - p) * (p < 0.08 ? p / 0.08 : 1);
      if (fade <= 0) continue;
      emberPaint.color =
          Color.lerp(colors.first, colors.last, p)!.withValues(alpha: fade);
      canvas.drawCircle(Offset(x, y), ember.size * (1 - p * 0.6), emberPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _FirePainter old) =>
      old.t != t || old.animating != animating;
}
