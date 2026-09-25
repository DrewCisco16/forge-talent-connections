import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// A small capitalised section heading.
class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Text(
      text.toUpperCase(),
      style: TextStyle(
        fontFamily: ForgeType.bodyFamily,
        fontSize: 10,
        fontWeight: FontWeight.bold,
        letterSpacing: 1.1,
        color: forge.textSub,
      ),
    );
  }
}

/// A plain surface card used to group content.
class ForgeCard extends StatelessWidget {
  const ForgeCard({
    required this.child,
    this.borderColor,
    this.borderWidth = 1,
    this.background,
    super.key,
  });

  final Widget child;
  final Color? borderColor;
  final double borderWidth;
  final Color? background;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: background ?? forge.surface,
        borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
        border: Border.all(
          color: borderColor ?? forge.strokeSoft,
          width: borderWidth,
        ),
      ),
      padding: const EdgeInsets.all(ForgeSpacing.cardPad),
      child: child,
    );
  }
}

/// Text painted with the gold gradient, used for the wordmark and headings.
class GoldGradientText extends StatelessWidget {
  const GoldGradientText(
    this.text, {
    required this.style,
    this.textAlign,
    super.key,
  });

  final String text;
  final TextStyle style;
  final TextAlign? textAlign;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return ShaderMask(
      shaderCallback: (Rect bounds) =>
          LinearGradient(colors: forge.goldGradient).createShader(bounds),
      child: Text(
        text,
        textAlign: textAlign,
        style: style.copyWith(color: Colors.white),
      ),
    );
  }
}

/// A marker that the data on screen is sample data, not a real record.
///
/// This build has no backend. Everything displayed is a fixture, and saying so
/// plainly is the same fail-closed principle the rest of the UI follows: a
/// viewer must never mistake demo content for a proven fact.
class DemoBadge extends StatelessWidget {
  const DemoBadge({super.key});

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: forge.violet.withValues(alpha: 0.14),
        border: Border.all(color: forge.violet.withValues(alpha: 0.5)),
        borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      child: Text(
        "DEMO · SAMPLE DATA",
        style: TextStyle(
          fontFamily: ForgeType.bodyFamily,
          fontSize: ForgeType.chip,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
          color: forge.violet,
        ),
      ),
    );
  }
}

/// The label shown on any AI-generated or AI-presented media.
class AiGeneratedLabel extends StatelessWidget {
  const AiGeneratedLabel({super.key});

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: ForgeColors.navyDeep.withValues(alpha: 0.82),
        border: Border.all(color: forge.cyan.withValues(alpha: 0.7)),
        borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(Icons.auto_awesome, size: 9, color: forge.cyan),
          const SizedBox(width: 4),
          Text(
            "AI-generated",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.chip,
              fontWeight: FontWeight.w700,
              color: forge.cyan,
            ),
          ),
        ],
      ),
    );
  }
}
