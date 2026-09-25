import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// The page header band used on form screens.
///
/// Carries the screen title, a supporting line, an optional back arrow and an
/// optional trailing chip (the next arrow, or a notification bell).
class HeroBand extends StatelessWidget {
  const HeroBand({
    required this.title,
    this.subtitle,
    this.onBack,
    this.trailing,
    super.key,
  });

  final String title;
  final String? subtitle;
  final VoidCallback? onBack;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: forge.heroGradient,
        ),
        borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
        border: Border.all(color: forge.strokeSoft),
      ),
      padding: const EdgeInsets.all(ForgeSpacing.cardPad),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (onBack != null) ...<Widget>[
            InkWell(
              onTap: onBack,
              child: Icon(Icons.arrow_back, size: 20, color: forge.text),
            ),
            const SizedBox(width: 12),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: TextStyle(
                    fontFamily: ForgeType.displayFamily,
                    fontSize: ForgeType.heroTitle,
                    fontWeight: FontWeight.bold,
                    color: forge.text,
                    height: 1.15,
                  ),
                ),
                if (subtitle != null) ...<Widget>[
                  const SizedBox(height: 4),
                  Text(
                    subtitle!,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.body,
                      color: forge.textSub,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null) ...<Widget>[
            const SizedBox(width: 12),
            trailing!,
          ],
        ],
      ),
    );
  }
}
