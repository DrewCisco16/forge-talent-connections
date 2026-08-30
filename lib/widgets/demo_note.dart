import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// Honest feedback for actions whose real work lives on the backend.
///
/// The demo never fakes an outcome: a control that cannot complete its job
/// here says so, in the app's own voice, instead of pretending or doing
/// nothing at all.
void demoNote(BuildContext context, String message) {
  final ForgeTheme forge = ForgeTheme.of(context);
  ScaffoldMessenger.of(context)
    ..clearSnackBars()
    ..showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        backgroundColor: forge.surface2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: BorderSide(color: forge.strokeSoft),
        ),
        content: Text(
          message,
          style: TextStyle(
            fontFamily: ForgeType.bodyFamily,
            fontSize: ForgeType.caption,
            height: 1.35,
            color: forge.text,
          ),
        ),
      ),
    );
}
