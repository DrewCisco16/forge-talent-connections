import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// A gold-sealed statement card.
///
/// Used where the product asserts that something is sealed and tamper-evident,
/// such as the service record note on A4 and the certificate card on D1.
class SealCard extends StatelessWidget {
  const SealCard({
    required this.text,
    this.title,
    this.rows = const <MapEntry<String, String>>[],
    super.key,
  });

  final String text;
  final String? title;

  /// Optional label/value rows rendered beneath the statement. All values are
  /// fixtures supplied by the caller; this widget asserts nothing itself.
  final List<MapEntry<String, String>> rows;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: forge.surface,
        borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
        border: Border.all(color: forge.gold, width: 2),
      ),
      padding: const EdgeInsets.all(ForgeSpacing.cardPad),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(colors: forge.goldGradient),
                ),
                child: const Icon(Icons.workspace_premium,
                    size: 17, color: Colors.white),
              ),
              const SizedBox(width: 10),
              if (title != null)
                Expanded(
                  child: Text(
                    title!,
                    style: TextStyle(
                      fontFamily: ForgeType.displayFamily,
                      fontSize: 19,
                      fontWeight: FontWeight.bold,
                      color: forge.gold,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            text,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              height: 1.35,
              color: forge.text,
            ),
          ),
          if (rows.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Divider(color: forge.strokeSoft, height: 1),
            const SizedBox(height: 10),
            for (final MapEntry<String, String> row in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: <Widget>[
                    Flexible(
                      child: Text(
                        row.key,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          color: forge.textSub,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      row.value,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        fontWeight: FontWeight.w700,
                        color: forge.text,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}
