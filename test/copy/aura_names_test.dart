import "dart:io";

import "package:flutter_test/flutter_test.dart";

/// Selective-aura boundary: certain platforms are internal strategy
/// analogies only and must never appear in product copy or source.
void main() {
  test("strategy-analogy platform names never appear in lib", () {
    final List<String> banned = <String>["Facebook", "Raya", "Seeking.com"];
    final List<String> offences = <String>[];

    for (final FileSystemEntity entity in Directory(
      "lib",
    ).listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith(".dart")) continue;
      final String content = entity.readAsStringSync();
      for (final String word in banned) {
        if (content.contains(word)) {
          offences.add("${entity.path} contains $word");
        }
      }
    }

    expect(offences, isEmpty, reason: offences.join("\n"));
  });
}
