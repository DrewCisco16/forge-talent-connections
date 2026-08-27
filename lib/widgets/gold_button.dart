import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// The primary call to action: a gold gradient pill.
///
/// Reserved for the primary action on a screen, as the design tokens specify
/// `primary_cta: gold_gradient`. Never used for social actions.
class GoldButton extends StatelessWidget {
  const GoldButton({
    required this.label,
    required this.onPressed,
    this.icon,
    this.fullWidth = true,
    super.key,
  });

  final String label;

  /// A null callback renders the disabled appearance and blocks interaction.
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool fullWidth;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
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
              gradient: LinearGradient(colors: forge.goldGradient),
              borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: fullWidth ? MainAxisSize.max : MainAxisSize.min,
                children: <Widget>[
                  if (icon != null) ...<Widget>[
                    Icon(icon, size: 16, color: Colors.white),
                    const SizedBox(width: 8),
                  ],
                  Text(
                    label,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.cardTitle,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
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

/// The secondary call to action: a gold outlined pill on the page background.
class OutlineGoldButton extends StatelessWidget {
  const OutlineGoldButton({
    required this.label,
    required this.onPressed,
    this.icon,
    this.fullWidth = true,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool fullWidth;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    final bool enabled = onPressed != null;

    return Opacity(
      opacity: enabled ? 1 : 0.45,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
          child: Container(
            width: fullWidth ? double.infinity : null,
            decoration: BoxDecoration(
              border: Border.all(color: forge.gold, width: 1.5),
              borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 13),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: fullWidth ? MainAxisSize.max : MainAxisSize.min,
              children: <Widget>[
                if (icon != null) ...<Widget>[
                  Icon(icon, size: 16, color: forge.gold),
                  const SizedBox(width: 8),
                ],
                Text(
                  label,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.cardTitle,
                    fontWeight: FontWeight.w700,
                    color: forge.gold,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
