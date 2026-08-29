import "dart:io";

import "package:flutter_test/flutter_test.dart";

/// House typography rule: no em-dashes or en-dashes anywhere in the app
/// source. Copy uses periods, commas, and plain hyphens instead.
void main() {
  test("no em-dashes or en-dashes anywhere in lib", () {
    final List<String> offences = <String>[];

    for (final FileSystemEntity entity in Directory(
      "lib",
    ).listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith(".dart")) continue;
      final List<String> lines = entity.readAsLinesSync();
      for (int i = 0; i < lines.length; i++) {
        if (lines[i].contains("—") || lines[i].contains("–")) {
          offences.add("${entity.path}:${i + 1}");
        }
      }
    }

    expect(
      offences,
      isEmpty,
      reason:
          "Em-dashes and en-dashes are banned. Found:\n"
          "${offences.join("\n")}",
    );
  });
}
