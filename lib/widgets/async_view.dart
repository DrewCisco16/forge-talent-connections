import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// Renders an asynchronous value fail-closed.
///
/// While the answer is unknown this shows a pending state, never an optimistic
/// placeholder that looks like success. When the request fails it says so
/// plainly, with the reason, rather than showing empty content that could be
/// mistaken for "nothing to report".
class AsyncView<T> extends StatelessWidget {
  const AsyncView({
    required this.value,
    required this.builder,
    this.pendingLabel = "Checking",
    this.onRetry,
    super.key,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final String pendingLabel;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return value.when(
      data: builder,
      loading: () => Padding(
        padding: const EdgeInsets.symmetric(vertical: 28),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: forge.textSub,
              ),
            ),
            const SizedBox(width: 10),
            Text(
              pendingLabel,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.body,
                color: forge.textSub,
              ),
            ),
          ],
        ),
      ),
      error: (Object error, StackTrace _) => Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: forge.red.withValues(alpha: 0.10),
          border: Border.all(color: forge.red.withValues(alpha: 0.45)),
          borderRadius: BorderRadius.circular(14),
        ),
        padding: const EdgeInsets.all(13),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Icon(Icons.error_outline, size: 15, color: forge.red),
                const SizedBox(width: 8),
                Text(
                  "Could not load this",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.body,
                    fontWeight: FontWeight.w700,
                    color: forge.red,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              "Nothing is shown rather than showing something unverified. $error",
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.caption,
                height: 1.35,
                color: forge.text,
              ),
            ),
            if (onRetry != null) ...<Widget>[
              const SizedBox(height: 10),
              InkWell(
                onTap: onRetry,
                child: Text(
                  "Try again",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    fontWeight: FontWeight.w700,
                    color: forge.gold,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
