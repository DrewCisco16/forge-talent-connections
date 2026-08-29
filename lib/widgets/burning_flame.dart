import "dart:math" as math;
import "dart:ui" as ui;

import "package:flutter/material.dart";
import "package:flutter/services.dart" show ByteData, rootBundle;

import "../theme/forge_theme.dart";

/// The burning flame: the original mark, with a subtle burn at its crown.
///
/// The logo itself is never transformed - no pulsing, no scaling. The burn is
/// a small cluster of flame tongues riding the top of the mark and stepping
/// down its right edge, each waving on its own phase and frequency so they
/// lick upward organically rather than throbbing in unison, plus a few rising
/// embers and a faint breathing halo.
/// Complementary and subtle: the mark stays the subject, the fire is an
/// accent at its tip, never a bonfire behind it.
///
/// The fire is shaped to the logo: the whole widget is exactly the mark's
/// bounding box, the painter is hard-clipped to it, and tongue heights are
/// clamped inside it - so the burn never spills past the top or bottom of
/// the design.
///
/// Reduced motion: when `MediaQuery.disableAnimations` is set, no controller
/// runs and the static mark renders with a fixed soft glow - no fire is drawn,
/// because a frozen frame of flames reads as a smudge, not a burn.
class BurningFlame extends StatefulWidget {
  /// Aspect ratio of assets/brand/forge_flame.png (578 x 780). The widget's
  /// footprint is exactly the mark's box, so the fire cannot escape it.
  static const double logoAspect = 578 / 780;

  const BurningFlame({required this.asset, this.height = 132, super.key});

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
  late final List<_Tongue> _lineTongues;
  late final List<_Ember> _embers;
  bool _started = false;

  /// Alpha mask of the mark's interior line channels. Fire drawn through it
  /// fills the lines of the flame and can never overlap the gold shape,
  /// because the untouched artwork always paints on top.
  ui.Image? _lineMask;

  Future<void> _loadLineMask() async {
    try {
      final ByteData data = await rootBundle.load(
        "assets/brand/forge_flame_linefire_mask.png",
      );
      final ui.Codec codec = await ui.instantiateImageCodec(
        data.buffer.asUint8List(),
      );
      final ui.FrameInfo frame = await codec.getNextFrame();
      if (mounted) setState(() => _lineMask = frame.image);
    } catch (_) {
      // Fail closed to the previous look: no mask, no line fire.
    }
  }

  @override
  void initState() {
    super.initState();
    _loadLineMask();
    // Fixed seed: the fire looks alive but renders deterministically.
    final math.Random random = math.Random(7);
    // Anchor points (x, y as fractions of the box, relative size) where small
    // flames ride the mark. Deliberately asymmetric - one modest lick left of
    // the tip, the tallest just right of it, then a strengthening chain down
    // the right edge - so the burn follows the sweep of the mark's own curves
    // instead of sitting on it like a symmetric crown.
    const List<(double, double, double)> anchors = <(double, double, double)>[
      (0.30, 0.25, 0.65),
      (0.42, 0.22, 1.2),
      (0.49, 0.23, 0.95),
      (0.58, 0.26, 1.05),
      (0.68, 0.29, 0.9),
      (0.80, 0.36, 1.0),
      (0.84, 0.47, 0.9),
      (0.90, 0.57, 0.8),
    ];
    _tongues = <_Tongue>[
      for (final (double ax, double ay, double s) in anchors)
        _Tongue(random, ax: ax, ay: ay, size: s),
    ];
    _embers = <_Ember>[
      for (int i = 0; i < 14; i++)
        _Ember(random, anchors[random.nextInt(anchors.length)]),
    ];
    // The in-line fire: taller tongues rising from the foot of the mark up
    // through its channels. Same look and clock as the crown burn; the mask
    // decides where they show.
    final math.Random lineRandom = math.Random(11);
    const List<(double, double, double)> lineAnchors =
        <(double, double, double)>[
          // Full sweep, end to end: the outermost anchors sit under the
          // thin channels at the far left and far right of the mark, so
          // fire travels through every line, not just the middle ones.
          (0.16, 0.88, 0.8),
          (0.24, 0.92, 0.9),
          (0.34, 0.99, 1.1),
          (0.44, 1.0, 1.25),
          (0.54, 1.0, 1.15),
          (0.64, 0.97, 1.0),
          (0.74, 0.92, 0.95),
          (0.84, 0.86, 0.9),
          (0.92, 0.8, 0.75),
        ];
    _lineTongues = <_Tongue>[
      for (final (double ax, double ay, double sz) in lineAnchors)
        _Tongue(lineRandom, ax: ax, ay: ay, size: sz),
    ];
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
              // The fire - glow, waving tongues, embers - hard-clipped to the
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
              // Fire inside the lines of the flame: the same waving-tongue
              // animation as the crown burn, rising through the mark's
              // interior channels behind a transparent ground, masked so it
              // never overlaps the gold shape or leaves the design.
              if (_lineMask != null)
                CustomPaint(
                  painter: _LineFirePainter(
                    mask: _lineMask!,
                    tongues: _lineTongues,
                    t: _controller.value,
                    animating: _controller.isAnimating,
                    colors: forge.goldGradient,
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
  _Tongue(
    math.Random random, {
    required this.ax,
    required this.ay,
    required this.size,
  })
    // Integer cycles per loop keep the repeat seamless.
    : riseFreq = 1 + random.nextInt(3),
       swayFreq = 1 + random.nextInt(2),
       risePhase = random.nextDouble(),
       swayPhase = random.nextDouble(),
       width = 0.10 + random.nextDouble() * 0.08,
       height = 0.5 + random.nextDouble() * 0.45;

  /// Anchor of the flame's base, as fractions of the box.
  final double ax;
  final double ay;

  /// Relative scale of this tongue within the set.
  final double size;

  final int riseFreq;
  final int swayFreq;
  final double risePhase;
  final double swayPhase;

  /// Base width and nominal height, as fractions of the stage.
  final double width;
  final double height;
}

/// One ember's fixed characteristics; it rises from one of the flame anchors.
class _Ember {
  _Ember(math.Random random, (double, double, double) anchor)
    : ax = anchor.$1,
      ay = anchor.$2,
      phase = random.nextDouble(),
      lane = random.nextDouble() * 2 - 1,
      speed = 0.6 + random.nextDouble() * 0.8,
      size = 1.4 + random.nextDouble() * 2.2,
      sway = 0.5 + random.nextDouble() * 1.5;

  final double ax;
  final double ay;
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

  /// Where the artwork's tip sits: the mark tapers to its point at ~0.44 of
  /// the width (measured from the asset), right at the top of the box.
  static const double _tipX = 0.44;

  @override
  void paint(Canvas canvas, Size size) {
    final double cx = size.width * _tipX;
    final double breathe = animating
        ? 0.5 + 0.5 * math.sin(t * 2 * math.pi)
        : 0.5;

    // A faint warm halo behind the crown, breathing (fixed at rest). Small
    // enough that its blur fades out before the clip edges.
    final Paint glowPaint = Paint()
      ..color = colors.first.withValues(alpha: 0.10 + 0.07 * breathe)
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, size.height * 0.035);
    // The halo leans right of the tip, matching the asymmetric burn.
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(cx + size.width * 0.06, size.height * 0.16),
        width: size.width * 0.36,
        height: size.height * 0.16,
      ),
      glowPaint,
    );
    // And a fainter one along the right edge, where the side flames ride.
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(size.width * 0.84, size.height * 0.44),
        width: size.width * 0.16,
        height: size.height * 0.30,
      ),
      glowPaint,
    );

    // At rest (reduced motion) no fire is drawn - only the soft glow above.
    if (!animating) return;

    // Two passes of small tongues riding the mark - a dim layer and a
    // brighter, tighter one, both behind the logo - clustered at the crown
    // and stepping down the right edge of the silhouette, so short flames
    // lick up around the tip and along the right side. Complementary, not a
    // bonfire: the mark stays the subject. Each waves on its own frequencies.
    for (final (double scale, double alpha, Color color, double blur)
        in <(double, double, Color, double)>[
          (1.0, 0.30, colors.last, 3),
          (0.75, 0.46, colors.first, 2),
        ]) {
      final Paint paint = Paint()
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, blur);

      for (final _Tongue tongue in tongues) {
        final double rise = math.sin(
          2 * math.pi * (tongue.riseFreq * t + tongue.risePhase),
        );
        final double sway = math.sin(
          2 * math.pi * (tongue.swayFreq * t + tongue.swayPhase),
        );

        // Each tongue rises from its own anchor on the mark. Tips are
        // clamped inside the top of the box; anchors sit far enough from
        // the sides that flanks, sway, and blur fade before the clip edges.
        final double base = size.height * tongue.ay;
        final double tongueHeight =
            (size.height *
                    tongue.height *
                    0.28 *
                    scale *
                    tongue.size *
                    (0.78 + 0.22 * rise))
                .clamp(0.0, base - size.height * 0.03);
        final double halfWidth =
            size.width * tongue.width * scale * tongue.size * 0.30;
        final double x = size.width * tongue.ax;
        final double tipX = x + sway * halfWidth * 1.6;
        final double tipY = base - tongueHeight;

        final Path path = Path()
          ..moveTo(x - halfWidth, base)
          // Left flank bows outward low and pulls in toward the waving tip.
          ..quadraticBezierTo(
            x - halfWidth * 1.15,
            base - tongueHeight * 0.45,
            tipX,
            tipY,
          )
          // Right flank mirrors back down to the crown.
          ..quadraticBezierTo(
            x + halfWidth * 1.15,
            base - tongueHeight * 0.45,
            x + halfWidth,
            base,
          )
          ..close();

        paint.color = color.withValues(alpha: alpha * (0.8 + 0.2 * rise.abs()));
        canvas.drawPath(path, paint);
      }
    }

    // A few embers drifting up from the flame anchors.
    final Paint emberPaint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1.5);
    for (final _Ember ember in embers) {
      final double p = (t * ember.speed + ember.phase) % 1.0;
      final double x =
          size.width * ember.ax +
          ember.lane * size.width * 0.05 +
          math.sin(p * ember.sway * 2 * math.pi + ember.phase * 6) *
              size.width *
              0.03 *
              p;
      final double y = size.height * ember.ay - p * size.height * 0.16;
      final double fade = 0.85 * (1 - p) * (p < 0.08 ? p / 0.08 : 1);
      if (fade <= 0) continue;
      emberPaint.color = Color.lerp(
        colors.first,
        colors.last,
        p,
      )!.withValues(alpha: fade);
      canvas.drawCircle(
        Offset(x, y),
        ember.size * 0.6 * (1 - p * 0.6),
        emberPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _FirePainter old) =>
      old.t != t || old.animating != animating;
}

/// Paints the crown-style flame animation inside the mark's line channels.
///
/// The ground is fully transparent: nothing is filled. Only the waving
/// tongues render, in the same two-pass gold palette, wave math, and clock
/// as the crown burn, and the interior alpha mask then keeps every stroke
/// inside the lines of the flame. Under reduced motion nothing is drawn,
/// exactly like the crown fire.
class _LineFirePainter extends CustomPainter {
  const _LineFirePainter({
    required this.mask,
    required this.tongues,
    required this.t,
    required this.animating,
    required this.colors,
  });

  final ui.Image mask;
  final List<_Tongue> tongues;
  final double t;
  final bool animating;
  final List<Color> colors;

  @override
  void paint(Canvas canvas, Size size) {
    if (!animating) return;

    final Rect rect = Offset.zero & size;
    canvas.saveLayer(rect, Paint());

    // Identical rendering to the crown burn: a dim wide pass and a bright
    // tight pass, each tongue waving on its own frequencies - only taller,
    // so the flames sweep up through the channels.
    for (final (double scale, double alpha, Color color, double blur)
        in <(double, double, Color, double)>[
          (1.0, 0.34, colors.last, 3),
          (0.75, 0.5, colors.first, 2),
        ]) {
      final Paint paint = Paint()
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, blur);

      for (final _Tongue tongue in tongues) {
        final double rise = math.sin(
          2 * math.pi * (tongue.riseFreq * t + tongue.risePhase),
        );
        final double sway = math.sin(
          2 * math.pi * (tongue.swayFreq * t + tongue.swayPhase),
        );

        final double base = size.height * tongue.ay;
        final double tongueHeight =
            (size.height *
                    tongue.height *
                    0.95 *
                    scale *
                    tongue.size *
                    (0.78 + 0.22 * rise))
                .clamp(0.0, base - size.height * 0.04);
        final double halfWidth =
            size.width * tongue.width * scale * tongue.size * 0.55;
        final double x = size.width * tongue.ax;
        final double tipX = x + sway * halfWidth * 1.4;
        final double tipY = base - tongueHeight;

        final Path path = Path()
          ..moveTo(x - halfWidth, base)
          ..quadraticBezierTo(
            x - halfWidth * 1.15,
            base - tongueHeight * 0.45,
            tipX,
            tipY,
          )
          ..quadraticBezierTo(
            x + halfWidth * 1.15,
            base - tongueHeight * 0.45,
            x + halfWidth,
            base,
          )
          ..close();

        paint.color = color.withValues(alpha: alpha * (0.8 + 0.2 * rise.abs()));
        canvas.drawPath(path, paint);
      }
    }

    // Keep only what falls inside the lines of the flame.
    canvas.drawImageRect(
      mask,
      Rect.fromLTWH(0, 0, mask.width.toDouble(), mask.height.toDouble()),
      rect,
      Paint()..blendMode = BlendMode.dstIn,
    );

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _LineFirePainter oldDelegate) =>
      oldDelegate.t != t || oldDelegate.mask != mask;
}
