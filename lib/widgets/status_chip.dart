import "package:flutter/material.dart";

import "../models/verification_status.dart";
import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// The verification state badge.
///
/// Colours follow the semantic mapping in the design tokens: verified is green,
/// pending and unverified take the sub colour, failed and locked are red.
/// Nothing here computes a state; the chip renders the state it is handed.
class StatusChip extends StatelessWidget {
  const StatusChip({required this.status, this.dense = false, super.key});

  final VerificationStatus status;
  final bool dense;

  /// The label shown for each state. These are the only five permitted.
  String get _label => switch (status) {
        VerificationStatus.verified => "VERIFIED",
        VerificationStatus.pending => "PENDING",
        VerificationStatus.unverified => "UNVERIFIED",
        VerificationStatus.failed => "FAILED",
        VerificationStatus.locked => "LOCKED",
      };

  IconData get _icon => switch (status) {
        VerificationStatus.verified => Icons.check_circle,
        VerificationStatus.pending => Icons.schedule,
        VerificationStatus.unverified => Icons.remove_circle_outline,
        VerificationStatus.failed => Icons.cancel,
        VerificationStatus.locked => Icons.lock,
      };

  Color _color(ForgeTheme forge) => switch (status) {
        VerificationStatus.verified => forge.green,
        VerificationStatus.pending => forge.textSub,
        VerificationStatus.unverified => forge.textSub,
        VerificationStatus.failed => forge.red,
        VerificationStatus.locked => forge.red,
      };

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    final Color color = _color(forge);

    return Container(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        border: Border.all(color: color.withValues(alpha: 0.55)),
        borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: dense ? 7 : 9,
        vertical: dense ? 3 : 4,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(_icon, size: dense ? 9 : 11, color: color),
          const SizedBox(width: 4),
          Text(
            _label,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.chip,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
