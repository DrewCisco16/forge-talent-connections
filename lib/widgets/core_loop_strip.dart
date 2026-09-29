import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";
import "section_label.dart";

/// The product reduced to what must be true: five steps, in order, with the
/// two-human rule underneath. Shown where a person first needs the whole
/// shape of the thing (the Mission screen and the dashboard) so no feature
/// is ever met without knowing which step it serves.
class CoreLoopStrip extends StatelessWidget {
  const CoreLoopStrip({super.key});

  static const List<String> steps = <String>[
    "Invitation",
    "Proof",
    "Vouch",
    "Project",
    "Sealed Record",
  ];

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return ForgeCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(
            "How It Works",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.cardTitle,
              fontWeight: FontWeight.w700,
              color: forge.gold,
            ),
          ),
          const SizedBox(height: 10),
          // Wrap, not Row: at large text sizes the five steps flow onto a
          // second line instead of clipping.
          Wrap(
            spacing: 6,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              for (int i = 0; i < steps.length; i++) ...<Widget>[
                _Step(number: i + 1, label: steps[i]),
                if (i < steps.length - 1)
                  ExcludeSemantics(
                    child: Icon(
                      Icons.arrow_forward_rounded,
                      size: 14,
                      color: forge.gold.withValues(alpha: 0.7),
                    ),
                  ),
              ],
            ],
          ),
          const SizedBox(height: 10),
          Text(
            "Nothing opens without proof. Two humans decide at every step.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.4,
              color: forge.textSub,
            ),
          ),
        ],
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.number, required this.label});

  final int number;
  final String label;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    // A rich text, not a Row: inside the Wrap the label can break across
    // lines at large text sizes instead of pushing past the card's edge.
    return Text.rich(
      TextSpan(
        children: <InlineSpan>[
          WidgetSpan(
            alignment: PlaceholderAlignment.middle,
            child: Container(
              width: 22,
              height: 22,
              alignment: Alignment.center,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: ForgeColors.goldGradient,
                ),
              ),
              // The badge keeps its size; the label beside it scales.
              child: Text(
                "$number",
                textScaler: TextScaler.noScaling,
                style: const TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.caption,
                  fontWeight: FontWeight.w700,
                  color: ForgeColors.navyDeep,
                ),
              ),
            ),
          ),
          TextSpan(text: " $label"),
        ],
      ),
      style: TextStyle(
        fontFamily: ForgeType.bodyFamily,
        fontSize: ForgeType.body,
        fontWeight: FontWeight.w600,
        color: forge.text,
      ),
    );
  }
}
