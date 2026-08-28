import "dart:math" as math;

import "package:flutter/material.dart";

/// A one-shot confetti burst, played over the moment a vouch is sealed.
///
/// The burst is celebration, not information: it plays once, ignores
/// pointers, and paints nothing after it finishes. Under reduced motion it
/// paints nothing at all — the signed state itself is the confirmation, so
/// nobody is stranded behind an animation they cannot see.
class ConfettiBurst extends StatefulWidget {
  const ConfettiBurst({
    required this.play,
    required this.colors,
    this.particleCount = 64,
    this.duration = const Duration(milliseconds: 1500),
    super.key,
  });

  /// Rising edge starts one burst; falling back to false paints nothing.
  final bool play;

  /// Confetti palette, passed in from the theme.
  final List<Color> colors;

  final int particleCount;
  final Duration duration;

  @override
  State<ConfettiBurst> createState() => _ConfettiBurstState();
}

class _ConfettiBurstState extends State<ConfettiBurst>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: widget.duration,
  );
  late List<_Particle> _particles = const <_Particle>[];

  @override
  void didUpdateWidget(ConfettiBurst old) {
    super.didUpdateWidget(old);
    if (widget.play && !old.play) _begin();
  }

  @override
  void initState() {
    super.initState();
    if (widget.play) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _begin();
      });
    }
  }

  void _begin() {
    if (MediaQuery.disableAnimationsOf(context)) return;
    // Seeded so a burst is reproducible under test.
    final math.Random rng = math.Random(7);
    _particles = List<_Particle>.generate(widget.particleCount, (int i) {
      final double angle =
          -math.pi / 2 + (rng.nextDouble() - 0.5) * math.pi * 1.15;
      final double speed = 0.55 + rng.nextDouble() * 1.05;
      return _Particle(
        vx: math.cos(angle) * speed,
        vy: math.sin(angle) * speed,
        spin: (rng.nextDouble() - 0.5) * 10,
        size: 3.0 + rng.nextDouble() * 4.5,
        color: widget.colors[i % widget.colors.length],
        drift: (rng.nextDouble() - 0.5) * 0.25,
        isRect: rng.nextBool(),
      );
    });
    _controller.forward(from: 0);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          if (!_controller.isAnimating || _particles.isEmpty) {
            return const SizedBox.expand();
          }
          return CustomPaint(
            size: Size.infinite,
            painter: _ConfettiPainter(
              particles: _particles,
              t: _controller.value,
            ),
          );
        },
      ),
    );
  }
}

class _Particle {
  const _Particle({
    required this.vx,
    required this.vy,
    required this.spin,
    required this.size,
    required this.color,
    required this.drift,
    required this.isRect,
  });

  final double vx;
  final double vy;
  final double spin;
  final double size;
  final Color color;
  final double drift;
  final bool isRect;
}

class _ConfettiPainter extends CustomPainter {
  const _ConfettiPainter({required this.particles, required this.t});

  final List<_Particle> particles;
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    // Launch point: horizontal centre, just above the bottom, which sits on
    // the hold control the burst celebrates.
    final Offset origin = Offset(size.width / 2, size.height * 0.82);
    final double reach = size.shortestSide;
    // Fade over the last third so the burst ends rather than stops.
    final double fade =
        t < 0.66 ? 1.0 : (1 - (t - 0.66) / 0.34).clamp(0.0, 1.0);
    final Paint paint = Paint();

    for (final _Particle p in particles) {
      final double x =
          origin.dx + (p.vx + p.drift * t) * reach * t * 0.9;
      final double y =
          origin.dy + p.vy * reach * t * 0.9 + 0.65 * reach * t * t;
      if (y > size.height + 12) continue;
      paint.color = p.color.withValues(alpha: fade);
      canvas.save();
      canvas.translate(x, y);
      canvas.rotate(p.spin * t);
      if (p.isRect) {
        canvas.drawRect(
          Rect.fromCenter(
              center: Offset.zero, width: p.size, height: p.size * 0.6),
          paint,
        );
      } else {
        canvas.drawCircle(Offset.zero, p.size / 2, paint);
      }
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ConfettiPainter old) =>
      old.t != t || old.particles != particles;
}
