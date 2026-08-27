import "package:flutter/material.dart";

import "tokens.dart";

/// The FORGE design system, exposed to widgets as a [ThemeExtension].
///
/// Widgets read colours from here rather than importing [ForgeColors] directly,
/// so a screen can be rendered against an alternate palette in tests without
/// touching widget code. Shape and spacing stay as compile-time constants on
/// [ForgeShape] and [ForgeSpacing] because they never vary by theme.
///
/// The vibe gradient is deliberately not carried here. It lives library-private
/// to the social action widgets so it cannot reach a form or governance surface.
@immutable
class ForgeTheme extends ThemeExtension<ForgeTheme> {
  const ForgeTheme({
    required this.bgGradient,
    required this.heroGradient,
    required this.surface,
    required this.surface2,
    required this.gold,
    required this.goldGradient,
    required this.goldDeep,
    required this.text,
    required this.textSub,
    required this.stroke,
    required this.strokeSoft,
    required this.violet,
    required this.coral,
    required this.cyan,
    required this.green,
    required this.red,
    required this.usmcScarlet,
  });

  /// The palette exactly as delivered in the design tokens.
  const ForgeTheme.standard()
      : bgGradient = const <Color>[
          ForgeColors.bgGradientTop,
          ForgeColors.bgGradientBottom,
        ],
        heroGradient = const <Color>[
          ForgeColors.heroGradientTop,
          ForgeColors.heroGradientBottom,
        ],
        surface = ForgeColors.surface,
        surface2 = ForgeColors.surface2,
        gold = ForgeColors.gold,
        goldGradient = ForgeColors.goldGradient,
        goldDeep = ForgeColors.goldDeep,
        text = ForgeColors.text,
        textSub = ForgeColors.textSub,
        stroke = ForgeColors.stroke,
        strokeSoft = ForgeColors.strokeSoft,
        violet = ForgeColors.violet,
        coral = ForgeColors.coral,
        cyan = ForgeColors.cyan,
        green = ForgeColors.green,
        red = ForgeColors.red,
        usmcScarlet = ForgeColors.usmcScarlet;

  final List<Color> bgGradient;
  final List<Color> heroGradient;
  final Color surface;
  final Color surface2;
  final Color gold;
  final List<Color> goldGradient;
  final Color goldDeep;
  final Color text;
  final Color textSub;
  final Color stroke;
  final Color strokeSoft;
  final Color violet;
  final Color coral;
  final Color cyan;
  final Color green;
  final Color red;
  final Color usmcScarlet;

  /// Reads the FORGE palette from [context].
  ///
  /// Falls back to [ForgeTheme.standard] so a widget rendered outside the app
  /// shell (a bare test harness, for instance) still paints correctly rather
  /// than throwing.
  static ForgeTheme of(BuildContext context) =>
      Theme.of(context).extension<ForgeTheme>() ?? const ForgeTheme.standard();

  @override
  ForgeTheme copyWith({
    List<Color>? bgGradient,
    List<Color>? heroGradient,
    Color? surface,
    Color? surface2,
    Color? gold,
    List<Color>? goldGradient,
    Color? goldDeep,
    Color? text,
    Color? textSub,
    Color? stroke,
    Color? strokeSoft,
    Color? violet,
    Color? coral,
    Color? cyan,
    Color? green,
    Color? red,
    Color? usmcScarlet,
  }) {
    return ForgeTheme(
      bgGradient: bgGradient ?? this.bgGradient,
      heroGradient: heroGradient ?? this.heroGradient,
      surface: surface ?? this.surface,
      surface2: surface2 ?? this.surface2,
      gold: gold ?? this.gold,
      goldGradient: goldGradient ?? this.goldGradient,
      goldDeep: goldDeep ?? this.goldDeep,
      text: text ?? this.text,
      textSub: textSub ?? this.textSub,
      stroke: stroke ?? this.stroke,
      strokeSoft: strokeSoft ?? this.strokeSoft,
      violet: violet ?? this.violet,
      coral: coral ?? this.coral,
      cyan: cyan ?? this.cyan,
      green: green ?? this.green,
      red: red ?? this.red,
      usmcScarlet: usmcScarlet ?? this.usmcScarlet,
    );
  }

  @override
  ForgeTheme lerp(covariant ForgeTheme? other, double t) {
    if (other == null) return this;
    List<Color> lerpStops(List<Color> a, List<Color> b) => <Color>[
          for (int i = 0; i < a.length; i++) Color.lerp(a[i], b[i], t)!,
        ];
    return ForgeTheme(
      bgGradient: lerpStops(bgGradient, other.bgGradient),
      heroGradient: lerpStops(heroGradient, other.heroGradient),
      surface: Color.lerp(surface, other.surface, t)!,
      surface2: Color.lerp(surface2, other.surface2, t)!,
      gold: Color.lerp(gold, other.gold, t)!,
      goldGradient: lerpStops(goldGradient, other.goldGradient),
      goldDeep: Color.lerp(goldDeep, other.goldDeep, t)!,
      text: Color.lerp(text, other.text, t)!,
      textSub: Color.lerp(textSub, other.textSub, t)!,
      stroke: Color.lerp(stroke, other.stroke, t)!,
      strokeSoft: Color.lerp(strokeSoft, other.strokeSoft, t)!,
      violet: Color.lerp(violet, other.violet, t)!,
      coral: Color.lerp(coral, other.coral, t)!,
      cyan: Color.lerp(cyan, other.cyan, t)!,
      green: Color.lerp(green, other.green, t)!,
      red: Color.lerp(red, other.red, t)!,
      usmcScarlet: Color.lerp(usmcScarlet, other.usmcScarlet, t)!,
    );
  }
}

/// Builds the application theme.
///
/// The type families named in the design tokens are declared here. The font
/// files themselves were not part of the handoff, so until they are supplied
/// the platform fallback renders instead. See TODO(licensed-art) below.
ThemeData buildForgeTheme() {
  const ForgeTheme forge = ForgeTheme.standard();

  // TODO(licensed-art): "Space Grotesk" and "Inter" are named in the design
  // tokens but no font files were delivered with the handoff package. Until the
  // TTFs are added to assets/ and registered in pubspec.yaml, Flutter falls back
  // to the platform default face. Sizes, weights and colours are already correct.
  TextStyle display(double size, FontWeight weight) => TextStyle(
        fontFamily: ForgeType.displayFamily,
        fontSize: size,
        fontWeight: weight,
        color: forge.text,
      );
  TextStyle body(double size, FontWeight weight, Color color) => TextStyle(
        fontFamily: ForgeType.bodyFamily,
        fontSize: size,
        fontWeight: weight,
        color: color,
      );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: ForgeColors.bgGradientBottom,
    colorScheme: const ColorScheme.dark(
      primary: ForgeColors.gold,
      surface: ForgeColors.surface,
      error: ForgeColors.red,
    ),
    textTheme: TextTheme(
      displayLarge: display(ForgeType.wordmark, FontWeight.bold),
      headlineLarge: display(ForgeType.heroTitle, FontWeight.bold),
      headlineMedium: display(ForgeType.screenTitle, FontWeight.bold),
      titleMedium: body(ForgeType.cardTitle, FontWeight.w700, forge.text),
      bodyMedium: body(ForgeType.body, FontWeight.w400, forge.text),
      bodySmall: body(ForgeType.caption, FontWeight.w400, forge.textSub),
      labelSmall: body(ForgeType.chip, FontWeight.w700, forge.text),
    ),
    extensions: const <ThemeExtension<dynamic>>[forge],
  );
}
