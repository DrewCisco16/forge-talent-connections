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
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final bool animate =
        widget.breathing && !MediaQuery.disableAnimationsOf(context);
    if (animate && _controller == null) {
      _controller = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 2400),
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
    final double width = widget.height * 188 / 227;

    Widget mark = Image.asset(
      kPhoenixMedallion,
      height: widget.height,
      width: width,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
    );
    final AnimationController? controller = _controller;
    if (controller != null) {
      mark = AnimatedBuilder(
        animation: controller,
        builder: (BuildContext context, Widget? child) => Transform.scale(
          scale: 1 + 0.022 * Curves.easeInOut.transform(controller.value),
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
                      forge.gold.withValues(alpha: 0.30),
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
