import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// The operating company's mark, small and quiet at the foot of a page.
///
/// FORGE LINK LLC owns and operates the FORGE Talent Connections software
/// application; this footer says so where a first-time visitor looks for
/// who stands behind a product: at the bottom, in small print, under the
/// polished gold mark. The logo asset carries its own metallic rendering,
/// so the gold reads as gold on the dark ground at any size.
class OperatorFooter extends StatelessWidget {
  const OperatorFooter({this.markHeight = 30, super.key});

  /// Height of the FORGE LINK mark; small by design, never dominant.
  final double markHeight;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Column(
      children: <Widget>[
        Image.asset(
          "assets/brand/forge_link_llc.png",
          height: markHeight,
          fit: BoxFit.contain,
          semanticLabel: "FORGE LINK LLC",
        ),
        const SizedBox(height: 7),
        Text(
          "FORGE Talent Connections is owned and operated by FORGE LINK LLC",
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: ForgeType.bodyFamily,
            fontSize: ForgeType.chip,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.2,
            height: 1.35,
            color: forge.textSub,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          "Incorporated in Delaware · Headquartered in Doral, Florida",
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: ForgeType.bodyFamily,
            fontSize: ForgeType.chip,
            height: 1.35,
            color: forge.textSub.withValues(alpha: 0.75),
          ),
        ),
      ],
    );
  }
}
