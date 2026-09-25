// Generates lib/theme/tokens.dart and lib/widgets/social_action.g.dart from the
// design handoff token file, so the Dart constants provably match the JSON.
//
// Run from the repository root:
//   dart run tool/generate_tokens.dart
//
// The source JSON lives in design_handoff/, which is deliberately not committed
// (it carries the Figma file key and engine names barred from this repo). Keep a
// local copy of the handoff package to regenerate.
import "dart:convert";
import "dart:io";

const String _source = "design_handoff/design_tokens.json";

/// Converts a "#RRGGBB" string into a Dart `Color` literal.
String _color(String hex) {
  final String v = hex.replaceAll("#", "").toUpperCase();
  if (v.length != 6) {
    throw FormatException("Expected a 6-digit hex color, got '$hex'");
  }
  return "Color(0xFF$v)";
}

/// Converts snake_case into lowerCamelCase.
String _camel(String key) {
  final List<String> parts = key.split("_");
  return parts.first +
      parts
          .skip(1)
          .map((String p) => p[0].toUpperCase() + p.substring(1))
          .join();
}

String _banner(String regenerate) =>
    """
// GENERATED FILE - DO NOT EDIT BY HAND.
//
// Source: $_source
// Regenerate: $regenerate
//
// Every value below is copied verbatim from the design token file. If a value
// here disagrees with the JSON, the JSON wins and this file is stale.
""";

void main() {
  final File file = File(_source);
  if (!file.existsSync()) {
    stderr.writeln("Cannot find $_source.");
    stderr.writeln(
      "The design handoff package must be present locally to regenerate tokens.",
    );
    exit(1);
  }

  final Map<String, dynamic> json =
      jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
  final Map<String, dynamic> meta = json["meta"] as Map<String, dynamic>;
  final Map<String, dynamic> color = json["color"] as Map<String, dynamic>;
  final Map<String, dynamic> type = json["type"] as Map<String, dynamic>;
  final Map<String, dynamic> scale = type["scale"] as Map<String, dynamic>;
  final Map<String, dynamic> shape = json["shape"] as Map<String, dynamic>;
  final Map<String, dynamic> spacing = json["spacing"] as Map<String, dynamic>;
  final Map<String, dynamic> motion = json["motion"] as Map<String, dynamic>;

  final String version = meta["version"] as String;
  final StringBuffer b = StringBuffer()
    ..writeln(_banner("dart run tool/generate_tokens.dart"))
    ..writeln('import "package:flutter/painting.dart";')
    ..writeln()
    ..writeln(
      "/// Version string of the token set these constants were generated from.",
    )
    ..writeln('const String kDesignTokenVersion = "$version";')
    ..writeln()
    ..writeln("/// Raw palette from the design system.")
    ..writeln("///")
    ..writeln(
      "/// The vibe gradient is intentionally absent: it is library-private to",
    )
    ..writeln(
      "/// the social action widgets so it cannot be painted onto forms or",
    )
    ..writeln("/// governance surfaces.")
    ..writeln("abstract final class ForgeColors {");

  // Flat colors and the two-stop background/hero gradients.
  final Map<String, dynamic> bg = color["bg_gradient"] as Map<String, dynamic>;
  final Map<String, dynamic> hero =
      color["hero_gradient"] as Map<String, dynamic>;
  b
    ..writeln("  /// ${bg["note"]}")
    ..writeln(
      "  static const Color bgGradientTop = ${_color(bg["top"] as String)};",
    )
    ..writeln(
      "  static const Color bgGradientBottom = ${_color(bg["bottom"] as String)};",
    )
    ..writeln("  /// ${hero["note"]}")
    ..writeln(
      "  static const Color heroGradientTop = ${_color(hero["top"] as String)};",
    )
    ..writeln(
      "  static const Color heroGradientBottom = ${_color(hero["bottom"] as String)};",
    );

  for (final MapEntry<String, dynamic> e in color.entries) {
    if (e.key == "bg_gradient" ||
        e.key == "hero_gradient" ||
        e.key == "semantic" ||
        e.key == "vibe_gradient") {
      continue;
    }
    if (e.value is String) {
      b.writeln(
        "  static const Color ${_camel(e.key)} = ${_color(e.value as String)};",
      );
    } else if (e.value is List) {
      final List<String> stops = (e.value as List<dynamic>)
          .map((dynamic c) => _color(c as String))
          .toList();
      b
        ..writeln("  static const List<Color> ${_camel(e.key)} = <Color>[")
        ..writeln("    ${stops.join(",\n    ")},")
        ..writeln("  ];");
    }
  }
  b
    ..writeln("}")
    ..writeln();

  // Semantic mapping, kept as a comment block so the intent travels with the code.
  final Map<String, dynamic> semantic =
      color["semantic"] as Map<String, dynamic>;
  b.writeln("/// Semantic colour assignments as stated in the token file.");
  for (final MapEntry<String, dynamic> e in semantic.entries) {
    b.writeln("/// - ${e.key}: ${e.value}");
  }
  b
    ..writeln("abstract final class ForgeSemantic {")
    ..writeln("  static const Color verified = ForgeColors.green;")
    ..writeln("  static const Color pending = ForgeColors.textSub;")
    ..writeln("  static const Color failedOrLocked = ForgeColors.red;")
    ..writeln(
      "  static const List<Color> primaryCta = ForgeColors.goldGradient;",
    )
    ..writeln("}")
    ..writeln();

  // Typography.
  final Map<String, dynamic> display = type["display"] as Map<String, dynamic>;
  final Map<String, dynamic> body = type["body"] as Map<String, dynamic>;
  b
    ..writeln("/// Type families and the fixed size scale.")
    ..writeln("abstract final class ForgeType {")
    ..writeln('  static const String displayFamily = "${display["family"]}";')
    ..writeln('  static const String bodyFamily = "${body["family"]}";');
  for (final MapEntry<String, dynamic> e in scale.entries) {
    b.writeln(
      "  static const double ${_camel(e.key)} = ${(e.value as num).toDouble()};",
    );
  }
  b
    ..writeln("}")
    ..writeln();

  // Shape.
  b
    ..writeln("/// Corner radii and the baseline phone frame.")
    ..writeln("abstract final class ForgeShape {");
  final List<String> phone = (shape["phone"] as String).split("x");
  b
    ..writeln("  static const double phoneWidth = ${double.parse(phone[0])};")
    ..writeln("  static const double phoneHeight = ${double.parse(phone[1])};");
  for (final MapEntry<String, dynamic> e in shape.entries) {
    if (e.key == "phone") continue;
    b.writeln(
      "  static const double ${_camel(e.key)} = ${(e.value as num).toDouble()};",
    );
  }
  b
    ..writeln("}")
    ..writeln();

  // Spacing.
  b
    ..writeln("/// Layout spacing steps.")
    ..writeln("abstract final class ForgeSpacing {");
  for (final MapEntry<String, dynamic> e in spacing.entries) {
    b.writeln(
      "  static const double ${_camel(e.key)} = ${(e.value as num).toDouble()};",
    );
  }
  b
    ..writeln("}")
    ..writeln();

  // Motion is prose in the token file. It is carried across verbatim as
  // documentation rather than invented durations; the motion pass lands in M4.
  b
    ..writeln("/// Motion intent, quoted from the token file.")
    ..writeln("///")
    ..writeln(
      "/// These are descriptions, not timings. No duration is invented here; the",
    )
    ..writeln("/// motion pass implements them against these notes.")
    ..writeln("abstract final class ForgeMotionNotes {");
  for (final MapEntry<String, dynamic> e in motion.entries) {
    b.writeln('  static const String ${_camel(e.key)} = "${e.value}";');
  }
  b.writeln("}");

  File("lib/theme/tokens.dart").writeAsStringSync(b.toString());

  // The vibe gradient is emitted as a part of the social action library, which
  // makes it library-private: no other file in the package can reference it.
  final List<String> vibe = (color["vibe_gradient"] as List<dynamic>)
      .map((dynamic c) => _color(c as String))
      .toList();
  final StringBuffer v = StringBuffer()
    ..writeln(_banner("dart run tool/generate_tokens.dart"))
    ..writeln('part of "social_action.dart";')
    ..writeln()
    ..writeln("/// ${semantic["social_action_only"]}")
    ..writeln("const List<Color> _kVibeGradient = <Color>[")
    ..writeln("  ${vibe.join(",\n  ")},")
    ..writeln("];");
  File("lib/widgets/social_action.g.dart").writeAsStringSync(v.toString());

  stdout.writeln(
    "Generated lib/theme/tokens.dart and lib/widgets/social_action.g.dart",
  );
  stdout.writeln("Token set version: $version");
}
