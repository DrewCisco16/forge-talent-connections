import "dart:math" as math;

import "package:flutter/material.dart";

import "../theme/forge_theme.dart";

/// The burning flame: the brand mark, actually alight.
///
/// Fire is drawn procedurally around the flame artwork — rising ember
/// particles and a breathing ground glow — while the mark itself flickers with
/// a small scale-and-sway. Everything is painted in the brand golds, so the
/// fire reads as the logo burning rather than an effect pasted behind it.
///
/// Reduced motion: when `MediaQuery.disableAnimations` is set, no controller
/// runs and the static flame renders with a fixed soft glow. The animation is
/// an enhancement, never a requirement for the splash to function.
class BurningFlame extends StatefulWidget {
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
    // One full particle cycle; phases spread the embers across it so the fire
    // has no visible loop seam.
    duration: const Duration(seconds: 2),
  );

  late final List<_Ember> _embers;
  bool _started = false;

  @override
  void initState() {
    super.initState();
    // Fixed seed: the fire looks alive but tests and goldens stay
    // deterministic frame for frame.
    final math.Random random = math.Random(7);
    _embers = List<_Ember>.generate(42, (_) => _Ember(random));
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
    // The stage leaves room above for rising embers and below for the glow.
    final double stageWidth = h * 1.5;
    final double stageHeight = h * 1.35;

    return SizedBox(
      width: stageWidth,
      height: stageHeight,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          final double t = _controller.value;
          final bool still = !_controller.isAnimating;
          // Flicker curves; at rest they collapse to their midpoints.
          final double breathe =
              still ? 0.5 : 0.5 + 0.5 * math.sin(t * 2 * math.pi);
          final double flicker = still
              ? 0
              : math.sin(t * 14 * math.pi) * 0.5 +
                  math.sin(t * 6 * math.pi) * 0.5;

          return Stack(
            alignment: Alignment.center,
            children: <Widget>[
              // Ground glow: the heat under the flame, breathing.
              Positioned(
                bottom: 0,
                child: Container(
                  width: h * 1.1,
                  height: h * 0.42,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: <BoxShadow>[
                      BoxShadow(
                        color: forge.gold
                            .withValues(alpha: 0.22 + 0.16 * breathe),
                        blurRadius: h * 0.42,
                        spreadRadius: h * 0.05,
                      ),
                    ],
                  ),
                ),
              ),
              // Rising embers, painted behind the mark.
              Positioned.fill(
                child: CustomPaint(
                  painter: _EmberPainter(
                    embers: _embers,
                    t: t,
                    animating: !still,
                    colors: forge.goldGradient,
                  ),
                ),
              ),
              // The mark itself, flickering: a small vertical stretch and sway,
              // the way a flame leans and recovers.
              Transform(
                alignment: Alignment.bottomCenter,
                transform: Matrix4.identity()
                  ..scaleByDouble(
                      1.0 + 0.012 * flicker, 1.0 + 0.03 * flicker, 1.0, 1.0)
                  ..rotateZ(0.010 * flicker),
                child: Image.asset(
                  widget.asset,
                  height: h,
                  fit: BoxFit.contain,
                  semanticLabel: "FORGE Talent Connections flame",
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

/// One ember's fixed characteristics; its motion comes from the shared clock.
class _Ember {
  _Ember(math.Random random)
      : phase = random.nextDouble(),
        lane = random.nextDouble() * 2 - 1,
        speed = 0.6 + random.nextDouble() * 0.8,
        size = 1.4 + random.nextDouble() * 2.4,
        sway = 0.5 + random.nextDouble() * 1.5;

  final double phase;

  /// Horizontal starting lane, -1..1 across the flame's width.
  final double lane;
  final double speed;
  final double size;
  final double sway;
}

class _EmberPainter extends CustomPainter {
  const _EmberPainter({
    required this.embers,
    required this.t,
    required this.animating,
    required this.colors,
  });

  final List<_Ember> embers;
  final double t;
  final bool animating;
  final List<Color> colors;

  @override
  void paint(Canvas canvas, Size size) {
    // At rest (reduced motion) the fire is not drawn at all: a static frame of
    // frozen sparks reads as dirt on the screen, not as fire.
    if (!animating) return;

    final double cx = size.width / 2;
    final double base = size.height * 0.86;
    final Paint paint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.5);

    for (final _Ember ember in embers) {
      final double p = (t * ember.speed + ember.phase) % 1.0;
      final double rise = p * size.height * 0.8;
      final double x = cx +
          ember.lane * size.width * 0.24 +
          math.sin(p * ember.sway * 2 * math.pi + ember.phase * 6) *
              size.width *
              0.05 *
              p;
      final double y = base - rise;
      final double fade = (1 - p) * (p < 0.08 ? p / 0.08 : 1);
      if (fade <= 0) continue;

      // Hotter (lighter gold) low, cooling to deep gold as it climbs.
      paint.color =
          Color.lerp(colors.first, colors.last, p)!.withValues(alpha: fade);
      canvas.drawCircle(Offset(x, y), ember.size * (1 - p * 0.6), paint);
    }
  }

  @override
  bool shouldRepaint(covariant _EmberPainter old) =>
      old.t != t || old.animating != animating;
}
