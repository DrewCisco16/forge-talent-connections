import "package:flutter/material.dart";
import "package:flutter/services.dart";

import "../theme/forge_theme.dart";

/// Adapts the phone-designed layout to whatever device it is running on.
///
/// Every screen in this app was specified at a 390x844 phone frame. On a tablet
/// that layout must not simply stretch: cards spanning an 11" iPad would give
/// line lengths nobody can read, and an avatar grid the size of a dinner plate.
/// So the content is held to a readable column and centred, with the page
/// gradient filling the rest of the glass.
///
/// This wraps the whole app, so the bottom navigation bar sits inside the same
/// column as the content rather than stretching away from it.
///
/// It also decides orientation. A phone stays portrait, because portrait is the
/// only layout the designs specify. A tablet is left free to rotate: the
/// centred column is already the same shape in both orientations, and locking
/// an iPad to portrait is a thing users notice and dislike.
class ForgeDeviceFrame extends StatefulWidget {
  const ForgeDeviceFrame({required this.child, super.key});

  final Widget child;

  /// The widest the content column is allowed to become.
  ///
  /// The designs are drawn at 390. This allows a little more so a tablet does
  /// not look like a phone screenshot pasted onto glass, while keeping line
  /// lengths close to what was designed.
  static const double maxContentWidth = 480;

  /// At or above this shortest side, treat the device as a tablet.
  ///
  /// 600 is the conventional break: every iPad clears it, no iPhone does.
  static const double tabletBreakpoint = 600;

  @override
  State<ForgeDeviceFrame> createState() => _ForgeDeviceFrameState();
}

class _ForgeDeviceFrameState extends State<ForgeDeviceFrame> {
  bool? _lockedToPortrait;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final Size size = MediaQuery.sizeOf(context);
    final bool isPhone =
        size.shortestSide < ForgeDeviceFrame.tabletBreakpoint;
    if (_lockedToPortrait == isPhone) return;
    _lockedToPortrait = isPhone;
    SystemChrome.setPreferredOrientations(
      isPhone
          ? const <DeviceOrientation>[DeviceOrientation.portraitUp]
          : DeviceOrientation.values,
    );
  }

  @override
  Widget build(BuildContext context) {
    final MediaQueryData media = MediaQuery.of(context);
    if (media.size.width <= ForgeDeviceFrame.maxContentWidth) {
      return widget.child;
    }

    final ForgeTheme forge = ForgeTheme.of(context);

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: forge.bgGradient,
        ),
      ),
      child: Center(
        child: SizedBox(
          width: ForgeDeviceFrame.maxContentWidth,
          child: MediaQuery(
            // Inside the column the app is, for every purpose it cares about,
            // running on a narrow screen. Horizontal safe-area insets belong to
            // the glass outside the column, so they are dropped here; the
            // vertical ones still matter and are kept.
            data: media.copyWith(
              size: Size(
                ForgeDeviceFrame.maxContentWidth,
                media.size.height,
              ),
              padding: media.padding.copyWith(left: 0, right: 0),
              viewPadding: media.viewPadding.copyWith(left: 0, right: 0),
              viewInsets: media.viewInsets.copyWith(left: 0, right: 0),
            ),
            child: widget.child,
          ),
        ),
      ),
    );
  }
}
