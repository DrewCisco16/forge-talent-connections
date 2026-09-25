import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// A confidence readout against a required threshold.
///
/// Renders a value the backend reported (never computed here) as a bar with
/// a visible tick at the required line, so "97 of 95 required" or "88 of 95
/// required" reads at a glance. Below the line the bar shows the shortfall
/// in the caution colour - the meter never dresses a miss up as a pass.
class ConfidenceMeter extends StatelessWidget {
  const ConfidenceMeter({
    required this.value,
    required this.required_,
    this.pending = false,
    super.key,
  });

  /// The reported confidence, 0-100.
  final int value;

  /// The threshold the backend enforces, 0-100.
  final int required_;

  /// True while the check is still running; the bar renders empty.
  final bool pending;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    final bool cleared = !pending && value >= required_;
    final Color fill = pending
        ? forge.strokeSoft
        : (cleared ? forge.gold : forge.red);

    return Semantics(
      label: pending
          ? "Confidence check running, $required_ required"
          : "Confidence $value of $required_ required",
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final double w = constraints.maxWidth;
              return SizedBox(
                height: 14,
                child: Stack(
                  children: <Widget>[
                    // Track.
                    Positioned.fill(
                      top: 3,
                      bottom: 3,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: forge.surface2,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                    // Reported value.
                    Positioned(
                      left: 0,
                      top: 3,
                      bottom: 3,
                      width: w * (pending ? 0 : value.clamp(0, 100)) / 100,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: fill,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                    // The required line: a tick the bar must reach.
                    Positioned(
                      left: (w * required_.clamp(0, 100) / 100) - 1,
                      top: 0,
                      bottom: 0,
                      width: 2,
                      child: DecoratedBox(
                        decoration: BoxDecoration(color: forge.text),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: 5),
          Text(
            pending
                ? "Checking · $required_ required"
                : "$value of $required_ required"
                      "${cleared ? "" : " · below the line"}",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.chip,
              fontWeight: FontWeight.w600,
              color: cleared || pending ? forge.textSub : forge.red,
            ),
          ),
        ],
      ),
    );
  }
}
