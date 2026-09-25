import "dart:io";

import "package:flutter_test/flutter_test.dart";

/// Every title is written in Title Case: "The Road Ahead", never "The road
/// ahead".
///
/// A title is a HeroBand title, or a Text literal styled with a title role
/// (screenTitle, cardTitle, or the display family). Short joining words stay
/// lowercase unless they open or close the title. Section labels are exempt
/// because SectionLabel renders them in capitals, and body copy, hints, and
/// button sentences keep sentence case.
final RegExp _heroTitle = RegExp(r'HeroBand\(\s*title:\s*"([^"\n$]+)"');
final RegExp _textLiteral = RegExp(r'Text\(\s*((?:"[^"\n]*"\s*)+)');
final RegExp _titleStyle = RegExp(
  r"ForgeType\.(screenTitle|cardTitle)|displayFamily",
);
final RegExp _word = RegExp(r"[A-Za-z][A-Za-z'&]*");

const Set<String> _minorWords = <String>{
  "a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "as", //
  "at", "by", "in", "of", "on", "to", "up", "via", "with", "from", "into",
  "over", "per", "vs",
};

bool _isTitleCase(String title) {
  final List<String> words = _word
      .allMatches(title)
      .map((RegExpMatch m) => m[0]!)
      .toList();
  for (int i = 0; i < words.length; i++) {
    final String w = words[i];
    final bool inner = i > 0 && i < words.length - 1;
    if (inner && _minorWords.contains(w.toLowerCase())) continue;
    if (w[0] != w[0].toUpperCase()) return false;
  }
  return true;
}

void main() {
  test("the helper reads Title Case the way the founder writes it", () {
    expect(_isTitleCase("The Road Ahead"), isTrue);
    expect(_isTitleCase("Sign Out of FORGE Talent Connections?"), isTrue);
    expect(_isTitleCase("5-Week Build Streak"), isTrue);
    expect(_isTitleCase("The road ahead"), isFalse);
    expect(_isTitleCase("Welcome back."), isFalse);
  });

  test("every title in the app is written in Title Case", () {
    final List<String> offences = <String>[];

    for (final FileSystemEntity entity in Directory(
      "lib",
    ).listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith(".dart")) continue;
      final String src = entity.readAsStringSync();

      int lineOf(int offset) =>
          "\n".allMatches(src.substring(0, offset)).length + 1;

      for (final RegExpMatch m in _heroTitle.allMatches(src)) {
        if (!_isTitleCase(m[1]!)) {
          offences.add("${entity.path}:${lineOf(m.start)}  ${m[1]}");
        }
      }

      for (final RegExpMatch m in _textLiteral.allMatches(src)) {
        final String literal = RegExp(r'"([^"\n]*)"')
            .allMatches(m[1]!)
            .map((RegExpMatch p) => p[1]!)
            .join();
        if (literal.contains(r"$")) continue;
        // The style belongs to this Text only up to the next Text call.
        String window = src.substring(
          m.end,
          (m.end + 420).clamp(0, src.length),
        );
        final int next = window.indexOf("Text(");
        if (next != -1) window = window.substring(0, next);
        if (_titleStyle.hasMatch(window) && !_isTitleCase(literal)) {
          offences.add("${entity.path}:${lineOf(m.start)}  $literal");
        }
      }
    }

    expect(
      offences,
      isEmpty,
      reason:
          'Titles use Title Case, "The Road Ahead" style. Found:\n'
          "${offences.join("\n")}",
    );
  });
}
