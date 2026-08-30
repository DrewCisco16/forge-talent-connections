import "dart:io";

import "package:flutter_test/flutter_test.dart";

/// Vocabulary this product does not use.
///
/// FORGE is project collaboration software. A sponsor onboards someone onto a
/// project; nobody is hired, recruited, or screened as a candidate. Copy that
/// drifts into recruiting vocabulary reframes the product, so it fails here
/// rather than reaching a screen.
const List<String> _bannedWords = <String>[
  "hire",
  "hiring",
  "hired",
  "employer",
  "employers",
  "recruiter",
  "recruiters",
  "recruiting",
  "recruitment",
  "candidate",
  "candidates",
  "applicant",
  "applicants",
];

/// Matches a Dart string literal.
final RegExp _stringLiteral = RegExp(r'"([^"\\]|\\.)*"');

void main() {
  test("no recruiting vocabulary in user-facing copy", () {
    final List<String> offences = <String>[];

    for (final FileSystemEntity entity in Directory(
      "lib",
    ).listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith(".dart")) continue;

      final List<String> lines = entity.readAsLinesSync();
      for (int i = 0; i < lines.length; i++) {
        final String line = lines[i];
        // Comments explain intent and may name what is being avoided.
        if (line.trimLeft().startsWith("//") ||
            line.trimLeft().startsWith("///")) {
          continue;
        }
        for (final RegExpMatch m in _stringLiteral.allMatches(line)) {
          final String literal = m[0]!.toLowerCase();
          for (final String word in _bannedWords) {
            if (RegExp("\\b$word\\b").hasMatch(literal)) {
              offences.add("${entity.path}:${i + 1}  '$word' in ${m[0]}");
            }
          }
        }
      }
    }

    expect(
      offences,
      isEmpty,
      reason:
          "FORGE is project collaboration, not hiring. Found:\n"
          "${offences.join("\n")}",
    );
  });
}
