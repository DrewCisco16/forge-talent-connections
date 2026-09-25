import "package:flutter/material.dart";

import "../models/verification_status.dart";
import "../theme/forge_theme.dart";
import "../theme/tokens.dart";
import "status_chip.dart";

/// A social feed entry.
///
/// The footer action slot takes a social action widget from the caller, which
/// is how the vibe gradient reaches this card without this file being able to
/// paint it directly.
class FeedCard extends StatelessWidget {
  const FeedCard({
    required this.name,
    required this.event,
    required this.body,
    this.status,
    this.avatar,
    this.vouchCount,
    this.action,
    this.onMessage,
    super.key,
  });

  final String name;

  /// The event line, for instance "shipped a verified deliverable".
  final String event;
  final String body;
  final VerificationStatus? status;
  final ImageProvider<Object>? avatar;

  /// Fixture count supplied by the caller.
  final int? vouchCount;

  /// The social action for this card, supplied by the caller.
  final Widget? action;
  final VoidCallback? onMessage;

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
            children: <Widget>[
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(colors: forge.goldGradient),
                ),
                padding: const EdgeInsets.all(2),
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: forge.surface2,
                    image: avatar == null
                        ? null
                        : DecorationImage(image: avatar!, fit: BoxFit.cover),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Flexible(
                          child: Text(
                            name,
                            overflow: TextOverflow.ellipsis,
                            // Names carry the largest weight in the row.
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.name,
                              fontWeight: FontWeight.bold,
                              color: forge.text,
                            ),
                          ),
                        ),
                        if (status != null) ...<Widget>[
                          const SizedBox(width: 6),
                          StatusChip(status: status!, dense: true),
                        ],
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      event,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        color: forge.textSub,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          Text(
            body,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              height: 1.35,
              color: forge.text,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          Row(
            children: <Widget>[
              if (vouchCount != null) ...<Widget>[
                Icon(Icons.verified_outlined, size: 14, color: forge.gold),
                const SizedBox(width: 5),
                // Context, never a popularity score: the number states how
                // many people signed their name to this work. Flexible so
                // the phrase truncates on narrow screens instead of
                // overflowing.
                Flexible(
                  child: Text(
                    "Work vouched · $vouchCount",
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      fontWeight: FontWeight.w700,
                      color: forge.gold,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
              ],
              if (action != null) action!,
              const Spacer(),
              if (onMessage != null)
                // Flexible so the link truncates at large text sizes
                // rather than overflowing the card.
                Flexible(
                  child: InkWell(
                    onTap: onMessage,
                    child: Text(
                      "Message",
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        fontWeight: FontWeight.w700,
                        color: forge.textSub,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
