import "package:flutter/material.dart";

import "../models/verification_status.dart";
import "../theme/forge_theme.dart";
import "../theme/tokens.dart";
import "gold_button.dart";
import "status_chip.dart";

/// A credential row with its verification state.
///
/// The action button is shown only when the caller supplies one. A verified
/// credential offers no action, matching the B4 specification.
class CredentialCard extends StatelessWidget {
  const CredentialCard({
    required this.title,
    required this.status,
    this.meta,
    this.actionLabel,
    this.onAction,
    super.key,
  });

  final String title;
  final VerificationStatus status;

  /// Identifier and validity line. Fixture text supplied by the caller.
  final String? meta;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: forge.surface,
        borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
        border: Border.all(color: forge.strokeSoft),
      ),
      padding: const EdgeInsets.all(ForgeSpacing.cardPad),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.cardTitle,
                    fontWeight: FontWeight.w700,
                    color: forge.text,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              StatusChip(status: status, dense: true),
            ],
          ),
          if (meta != null) ...<Widget>[
            const SizedBox(height: 6),
            Text(
              meta!,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.caption,
                color: forge.textSub,
              ),
            ),
          ],
          if (actionLabel != null) ...<Widget>[
            const SizedBox(height: ForgeSpacing.gapCard),
            OutlineGoldButton(
              label: actionLabel!,
              onPressed: onAction,
            ),
          ],
        ],
      ),
    );
  }
}
