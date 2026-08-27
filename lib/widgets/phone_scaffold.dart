import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// The 390x844 screen frame with the standard vertical background gradient.
///
/// Every screen sits inside one of these. [bottomNav] is pinned below the
/// scrolling content; [fullBleed] drops the horizontal padding for the social
/// screens, which run edge to edge.
class PhoneScaffold extends StatelessWidget {
  const PhoneScaffold({
    required this.child,
    this.bottomNav,
    this.fullBleed = false,
    this.scrollable = true,
    super.key,
  });

  final Widget child;
  final Widget? bottomNav;
  final bool fullBleed;
  final bool scrollable;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    final Widget content = Padding(
      padding: EdgeInsets.symmetric(
        horizontal: fullBleed ? 0 : ForgeSpacing.screenPadX,
      ),
      child: child,
    );

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: forge.bgGradient,
        ),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          bottom: false,
          child: scrollable ? SingleChildScrollView(child: content) : content,
        ),
        bottomNavigationBar: bottomNav,
      ),
    );
  }
}
