import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// The tone of a banner, which selects its accent colour.
///
/// Governance and denial copy uses these; none of them may use the vibe
/// gradient, which is reserved for social actions.
enum BannerTone { info, governance, denial, coach }

/// An inline note: a tip, a governance statement, or an honest denial.
///
/// Denials are never softened and never rendered as success.
class BannerNote extends StatelessWidget {
  const BannerNote({
    required this.text,
    this.tone = BannerTone.info,
    this.icon,
    this.title,
    super.key,
  });

  final String text;
  final BannerTone tone;
  final IconData? icon;
  final String? title;

  Color _accent(ForgeTheme forge) => switch (tone) {
    BannerTone.info => forge.cyan,
    BannerTone.governance => forge.gold,
    BannerTone.denial => forge.red,
    BannerTone.coach => forge.violet,
  };

  IconData get _defaultIcon => switch (tone) {
    BannerTone.info => Icons.info_outline,
    BannerTone.governance => Icons.verified_user_outlined,
    BannerTone.denial => Icons.lock_outline,
    BannerTone.coach => Icons.lightbulb_outline,
  };

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    final Color accent = _accent(forge);

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.10),
        border: Border.all(color: accent.withValues(alpha: 0.45)),
        borderRadius: BorderRadius.circular(14),
      ),
      padding: const EdgeInsets.all(13),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon ?? _defaultIcon, size: 15, color: accent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (title != null) ...<Widget>[
                  Text(
                    title!,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.body,
                      fontWeight: FontWeight.w700,
                      color: accent,
                    ),
                  ),
                  const SizedBox(height: 3),
                ],
                Text(
                  text,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.body,
                    height: 1.35,
                    color: forge.text,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
