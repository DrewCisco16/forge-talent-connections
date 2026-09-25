import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";
import "section_label.dart";

/// The brand lockup as an even block, like the marketing sticker.
///
/// FORGE and TALENT CONNECTIONS are each fitted to exactly the same width,
/// with the gold rule spanning the same measure, so the two lines read as
/// one aligned unit: no ragged edges, one axis, one block. The em size of
/// each line is whatever makes it exactly [width] wide, which is what makes
/// the wordmark large and the descriptor proportionally strong beneath it.
class BrandLockup extends StatelessWidget {
  const BrandLockup({required this.width, this.showDivider = true, super.key});

  /// The block's width; both lines and the rule fit it exactly.
  final double width;

  /// The gold rule between the lines; the compact header omits it.
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    Widget line(Widget child) => SizedBox(
      width: width,
      child: FittedBox(fit: BoxFit.fitWidth, child: child),
    );

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        line(
          GoldGradientText(
            "FORGE",
            style: const TextStyle(
              fontFamily: ForgeType.displayFamily,
              // Scaled by the FittedBox; only the ratios matter here.
              fontSize: 100,
              fontWeight: FontWeight.w800,
              letterSpacing: 9,
              height: 1.02,
            ),
          ),
        ),
        if (showDivider) ...<Widget>[
          SizedBox(height: width * 0.035),
          Container(
            width: width,
            height: 1.5,
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: forge.goldGradient),
            ),
          ),
          SizedBox(height: width * 0.035),
        ] else
          SizedBox(height: width * 0.02),
        line(
          Text(
            "TALENT CONNECTIONS",
            maxLines: 1,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: 100,
              fontWeight: FontWeight.bold,
              letterSpacing: 6,
              height: 1.05,
              color: forge.text,
            ),
          ),
        ),
      ],
    );
  }
}
