import "dart:math" as math;

import "package:flutter/material.dart";

import "../mock/fixtures.dart";
import "../theme/forge_theme.dart";
import "../theme/tokens.dart";
import "gold_button.dart";

/// The phoenix medallion: the application's identity mark.
///
/// One asset, three roles. Full size it is the mark on the door pages
/// (splash, sign-in, mission). Small and pulsing it is the pending state,
/// so waiting reads as the brand breathing rather than a generic spinner.
/// Muted it anchors an empty state, so "nothing here" still looks like
/// this product. Under reduced motion every role is a still frame.
class PhoenixMedallion extends StatefulWidget {
  const PhoenixMedallion({
    required this.height,
    this.breathing = true,
    this.glow = true,
    super.key,
  });

  final double height;

  /// A slow scale breath, disabled under reduced motion.
  final bool breathing;

  /// The soft gold halo behind the metal.
  final bool glow;

  @override
  State<PhoenixMedallion> createState() => _PhoenixMedallionState();
}

class _PhoenixMedallionState extends State<PhoenixMedallion>
    with TickerProviderStateMixin {
  AnimationController? _breath;
  AnimationController? _sheen;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final bool reduced = MediaQuery.disableAnimationsOf(context);
    final bool breathe = widget.breathing && !reduced;
    if (breathe && _breath == null) {
      _breath = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 2400),
      )..repeat(reverse: true);
    } else if (!breathe && _breath != null) {
      _breath!.dispose();
      _breath = null;
    }
    // The shine runs whenever motion is allowed: a light sweep across the
    // metal and sparkle points on the ring and wing, on a 3.2 second loop.
    if (!reduced && _sheen == null) {
      _sheen = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 3200),
      )..repeat();
    } else if (reduced && _sheen != null) {
      _sheen!.dispose();
      _sheen = null;
    }
  }

  @override
  void dispose() {
    _breath?.dispose();
    _sheen?.dispose();
    super.dispose();
  }

  /// Where the sweep sits for a loop position: it crosses the mark during
  /// the first 40 percent of the loop and rests off the metal after that.
  static double _sweepX(double t) => t < 0.4 ? -1.8 + 3.6 * (t / 0.4) : 9;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    final double width = widget.height * 188 / 227;

    final Widget image = Image.asset(
      kPhoenixMedallion,
      height: widget.height,
      width: width,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
    );

    // The sheen is painted only where the metal is: srcATop keeps the
    // gradient inside the medallion's own alpha.
    Widget shone(double sweepX, double strength) => ShaderMask(
      blendMode: BlendMode.srcATop,
      shaderCallback: (Rect r) => LinearGradient(
        begin: Alignment(sweepX - 0.9, -1),
        end: Alignment(sweepX + 0.9, 1),
        colors: <Color>[
          const Color(0x00FFFFFF),
          const Color(0xFFFFF6DC).withValues(alpha: 0.18 * strength),
          Colors.white.withValues(alpha: 0.72 * strength),
          const Color(0xFFFFF6DC).withValues(alpha: 0.18 * strength),
          const Color(0x00FFFFFF),
        ],
        stops: const <double>[0.0, 0.42, 0.5, 0.58, 1.0],
      ).createShader(r),
      child: image,
    );

    final AnimationController? sheen = _sheen;
    Widget mark = sheen == null
        // Reduced motion: one resting highlight, no movement.
        ? shone(-0.35, 0.55)
        : AnimatedBuilder(
            animation: sheen,
            builder: (BuildContext context, Widget? child) => Stack(
              alignment: Alignment.center,
              children: <Widget>[
                shone(_sweepX(sheen.value), 1),
                CustomPaint(
                  size: Size(width, widget.height),
                  painter: _SparklePainter(sheen.value),
                ),
              ],
            ),
          );

    final AnimationController? breath = _breath;
    if (breath != null) {
      mark = AnimatedBuilder(
        animation: breath,
        builder: (BuildContext context, Widget? child) => Transform.scale(
          scale: 1 + 0.022 * Curves.easeInOut.transform(breath.value),
          child: child,
        ),
        child: mark,
      );
    }

    return Semantics(
      image: true,
      label: "FORGE Talent Connections phoenix medallion",
      child: SizedBox(
        width: width + widget.height * 0.5,
        height: widget.height + widget.height * 0.3,
        child: Stack(
          alignment: Alignment.center,
          children: <Widget>[
            if (widget.glow)
              Container(
                width: widget.height * 1.15,
                height: widget.height * 1.15,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: <Color>[
                      forge.gold.withValues(alpha: 0.34),
                      forge.gold.withValues(alpha: 0.0),
                    ],
                    stops: const <double>[0.0, 0.68],
                  ),
                ),
              ),
            mark,
          ],
        ),
      ),
    );
  }
}

/// Sparkle points on the metal: four-point stars that bloom and fade on
/// staggered clocks at fixed places on the ring and the wing.
class _SparklePainter extends CustomPainter {
  const _SparklePainter(this.t);

  final double t;

  /// Positions as fractions of the mark, and each star's phase offset.
  static const List<(double, double, double)> _points =
      <(double, double, double)>[
        (0.30, 0.42, 0.00),
        (0.63, 0.27, 0.36),
        (0.52, 0.71, 0.62),
        (0.21, 0.62, 0.84),
      ];

  @override
  void paint(Canvas canvas, Size size) {
    for (final (double fx, double fy, double phase) in _points) {
      // Each star lives for a fifth of the loop, then rests.
      final double local = ((t + phase) % 1.0) / 0.22;
      if (local >= 1) continue;
      final double a = math.sin(local * math.pi);
      final double r = size.height * 0.055 * (0.55 + 0.45 * a);
      final Offset c = Offset(fx * size.width, fy * size.height);
      final Paint glow = Paint()
        ..color = const Color(0xFFFFF3C4).withValues(alpha: 0.55 * a)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, r * 0.6);
      canvas.drawCircle(c, r * 0.55, glow);
      final Paint ray = Paint()
        ..color = Colors.white.withValues(alpha: 0.95 * a)
        ..strokeWidth = math.max(1, r * 0.16)
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(c - Offset(r, 0), c + Offset(r, 0), ray);
      canvas.drawLine(c - Offset(0, r), c + Offset(0, r), ray);
      final Paint diag = Paint()
        ..color = Colors.white.withValues(alpha: 0.55 * a)
        ..strokeWidth = math.max(0.8, r * 0.1)
        ..strokeCap = StrokeCap.round;
      final double d = r * 0.45;
      canvas.drawLine(c - Offset(d, d), c + Offset(d, d), diag);
      canvas.drawLine(c - Offset(d, -d), c + Offset(d, -d), diag);
    }
  }

  @override
  bool shouldRepaint(_SparklePainter old) => old.t != t;
}

/// The pending state: a small medallion breathing beside a label.
///
/// Waiting is honest here: the label says what is being checked, and the
/// pulse says the check is alive. Reduced motion shows the mark still.
class MedallionPending extends StatefulWidget {
  const MedallionPending({required this.label, super.key});

  final String label;

  @override
  State<MedallionPending> createState() => _MedallionPendingState();
}

class _MedallionPendingState extends State<MedallionPending>
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final bool animate = !MediaQuery.disableAnimationsOf(context);
    if (animate && _controller == null) {
      _controller = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 1100),
      )..repeat(reverse: true);
    } else if (!animate && _controller != null) {
      _controller!.dispose();
      _controller = null;
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    Widget mark = Image.asset(
      kPhoenixMedallion,
      height: 22,
      width: 22 * 188 / 227,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
    );
    final AnimationController? controller = _controller;
    mark = controller == null
        ? Opacity(opacity: 0.85, child: mark)
        : FadeTransition(
            opacity: Tween<double>(begin: 0.45, end: 1.0).animate(controller),
            child: mark,
          );

    return Semantics(
      liveRegion: true,
      label: widget.label,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            ExcludeSemantics(child: mark),
            const SizedBox(width: 10),
            Flexible(
              child: Text(
                widget.label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.body,
                  color: forge.textSub,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// An empty state that still belongs to the product.
///
/// A muted medallion, a plain title, one sentence of why, and at most one
/// way forward. Nothing here reads as an error: empty is a true, calm
/// answer, never a broken screen.
class EmptyState extends StatelessWidget {
  const EmptyState({
    required this.title,
    required this.body,
    this.actionLabel,
    this.onAction,
    super.key,
  });

  final String title;
  final String body;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: forge.surface,
        border: Border.all(color: forge.strokeSoft),
        borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
      ),
      padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
      child: Column(
        children: <Widget>[
          Opacity(
            opacity: 0.55,
            child: ExcludeSemantics(
              child: Image.asset(
                kPhoenixMedallion,
                height: 44,
                width: 44 * 188 / 227,
                fit: BoxFit.contain,
                filterQuality: FilterQuality.high,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            title,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.cardTitle,
              fontWeight: FontWeight.w700,
              color: forge.text,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            body,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.4,
              color: forge.textSub,
            ),
          ),
          if (actionLabel != null && onAction != null) ...<Widget>[
            const SizedBox(height: 14),
            OutlineGoldButton(label: actionLabel!, onPressed: onAction),
          ],
        ],
      ),
    );
  }
}
