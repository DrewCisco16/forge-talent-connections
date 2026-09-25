import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// A labelled form field on the surface2 box, with an optional help affordance.
class FieldBox extends StatelessWidget {
  const FieldBox({
    required this.label,
    this.value,
    this.hint,
    this.onHelp,
    this.maxLines = 1,
    super.key,
  });

  /// Rendered in caps as the field label.
  final String label;

  /// Prefilled content. Fixture text, never a production claim.
  final String? value;
  final String? hint;
  final VoidCallback? onHelp;
  final int maxLines;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Text(
              label.toUpperCase(),
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: 10,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.8,
                color: forge.textSub,
              ),
            ),
            if (onHelp != null) ...<Widget>[
              const SizedBox(width: 6),
              InkWell(
                onTap: onHelp,
                child: Icon(Icons.help_outline, size: 12, color: forge.textSub),
              ),
            ],
          ],
        ),
        const SizedBox(height: 6),
        Container(
          width: double.infinity,
          decoration: BoxDecoration(
            color: forge.surface2,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: forge.strokeSoft),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Text(
            value ?? hint ?? "",
            maxLines: maxLines,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              color: value == null ? forge.textSub : forge.text,
            ),
          ),
        ),
      ],
    );
  }
}
