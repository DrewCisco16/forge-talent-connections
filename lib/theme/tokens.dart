// GENERATED FILE - DO NOT EDIT BY HAND.
//
// Source: design_handoff/design_tokens.json
// Regenerate: dart run tool/generate_tokens.dart
//
// Every value below is copied verbatim from the design token file. If a value
// here disagrees with the JSON, the JSON wins and this file is stale.

import "package:flutter/painting.dart";

/// Version string of the token set these constants were generated from.
const String kDesignTokenVersion = "v4-dark-2026-08-28";

/// Raw palette from the design system.
///
/// The vibe gradient is intentionally absent: it is library-private to
/// the social action widgets so it cannot be painted onto forms or
/// governance surfaces.
abstract final class ForgeColors {
  /// vertical, every screen background
  static const Color bgGradientTop = Color(0xFF0F1A33);
  static const Color bgGradientBottom = Color(0xFF060B16);

  /// page header band on form screens
  static const Color heroGradientTop = Color(0xFF1A2647);
  static const Color heroGradientBottom = Color(0xFF0D142B);
  static const Color surface = Color(0xFF141E35);
  static const Color surface2 = Color(0xFF1C2945);
  static const Color navyDeep = Color(0xFF060B16);
  static const Color gold = Color(0xFFE3B341);
  static const List<Color> goldGradient = <Color>[
    Color(0xFFF2C759),
    Color(0xFFC79929),
  ];
  static const Color goldDeep = Color(0xFF9E7821);
  static const Color text = Color(0xFFF5F7FC);
  static const Color textSub = Color(0xFF93A0BC);
  static const Color stroke = Color(0xFF4D5C80);
  static const Color strokeSoft = Color(0xFF334059);
  static const Color violet = Color(0xFF9466FF);
  static const Color coral = Color(0xFFFF5973);
  static const Color cyan = Color(0xFF40D9FF);
  static const Color green = Color(0xFF38D9A9);
  static const Color red = Color(0xFFF04F6E);
  static const Color usmcScarlet = Color(0xFFB3141F);
}

/// Semantic colour assignments as stated in the token file.
/// - verified: green
/// - pending: text_sub
/// - failed_or_locked: red
/// - social_action_only: vibe_gradient (vouch, streak, share; never on forms or governance banners)
/// - primary_cta: gold_gradient
/// - cta_text_on_gold: #FFFFFF or navy_deep
abstract final class ForgeSemantic {
  static const Color verified = ForgeColors.green;
  static const Color pending = ForgeColors.textSub;
  static const Color failedOrLocked = ForgeColors.red;
  static const List<Color> primaryCta = ForgeColors.goldGradient;
}

/// Type families and the fixed size scale.
abstract final class ForgeType {
  static const String displayFamily = "Arial";
  static const String bodyFamily = "Arial";
  static const double heroTitle = 30.0;
  static const double screenTitle = 26.0;
  static const double wordmark = 44.0;
  static const double lockupDescriptor = 18.0;
  static const double name = 17.0;
  static const double cardTitle = 15.0;
  static const double body = 13.0;
  static const double caption = 11.0;
  static const double chip = 9.0;
}

/// Corner radii and the baseline phone frame.
abstract final class ForgeShape {
  static const double phoneWidth = 390.0;
  static const double phoneHeight = 844.0;
  static const double screenRadius = 28.0;
  static const double cardRadius = 18.0;
  static const double ctaRadius = 16.0;
  static const double pillRadius = 999.0;
}

/// Layout spacing steps.
abstract final class ForgeSpacing {
  static const double screenPadX = 20.0;
  static const double cardPad = 16.0;
  static const double gapSection = 16.0;
  static const double gapCard = 10.0;
}

/// Motion intent, quoted from the token file.
///
/// These are descriptions, not timings. No duration is invented here; the
/// motion pass implements them against these notes.
abstract final class ForgeMotionNotes {
  static const String cardEntrance = "spring, 60ms stagger";
  static const String scoreRing = "count-up then settle";
  static const String verifiedStamp = "tick + scale-settle + haptic";
  static const String vouchTap = "particle burst on vibe gradient + haptic";
  static const String denial = "soft shake + denial haptic; never fake success";
  static const String restraintNote =
      "Shipped MVP still under build-guide restraint rule unless Andrew revises; these specs are the concept target";
}
