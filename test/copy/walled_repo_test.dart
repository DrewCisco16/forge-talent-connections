import "dart:convert";
import "dart:io";

import "package:flutter_test/flutter_test.dart";

/// The walled-repo guard.
///
/// This repository is the consumer UI layer. Internal system names and patent
/// application numbers must not appear anywhere in it: not in a string, not in
/// a comment, not in an asset name, not in a route. Until now that rule was
/// checked by hand; this test makes the suite itself refuse them.
///
/// The banned terms are stored base64-encoded and decoded only at runtime,
/// because writing them literally here would put them in the repo - the exact
/// thing this test exists to prevent. The encoded forms never match the
/// decoded scan, so the test cannot flag itself.
///
/// Publication numbers were removed from this list on Andrew's explicit
/// override: published applications are public USPTO records, and the product
/// now displays them as provenance on the Trust Technology screen. Internal
/// system names stay barred - the override was for filings, not for engine
/// vocabulary.
///
/// The list also bars the prosecution and payment identifiers that appear on
/// USPTO filing receipts: customer number, Patent Center number, confirmation
/// number, payment transaction id, and card fragment. Those are account
/// credentials and financial data, not product provenance. The override
/// covered what identifies the invention publicly, never what grants access to
/// the file or the payment method behind it.
final List<String> _banned = <String>[
  "UEFDRE1HUw==",
  "UE1fREVDQUJT",
  "U0VEQ1BI",
  "U0VEQw==",
  "RGVjaXNpb25Ub2tlbg==",
  "MjIwODYx",
  "NzQ1NjU0NzM=",
  "OTEwMw==",
  "RTIwMjYyTUIwNTU5OTgyMQ==",
  "OTc2Nw==",
].map((String e) => utf8.decode(base64Decode(e))).toList();

/// Directories whose contents count as the repo's source of record.
const List<String> _roots = <String>["lib", "test", "tool", "assets"];

void main() {
  test("no internal system names or filing numbers anywhere in the source", () {
    final List<String> offences = <String>[];

    for (final String root in _roots) {
      final Directory dir = Directory(root);
      if (!dir.existsSync()) continue;

      for (final FileSystemEntity entity in dir.listSync(recursive: true)) {
        if (entity is! File) continue;

        // File and directory names are scanned for every entry; text content
        // is scanned where it can be read as text. Binary assets (images)
        // are covered by the name check.
        final String path = entity.path;
        for (final String term in _banned) {
          if (path.toUpperCase().contains(term.toUpperCase())) {
            offences.add("$path  (term in file path)");
          }
        }

        if (path.endsWith(".png") || path.endsWith(".jpg")) continue;

        final String content;
        try {
          content = entity.readAsStringSync();
        } on FileSystemException {
          continue; // Unreadable as text; the name check above still applied.
        }
        final String upper = content.toUpperCase();
        for (final String term in _banned) {
          if (upper.contains(term.toUpperCase())) {
            offences.add("$path  (term in content)");
          }
        }
      }
    }

    expect(
      offences,
      isEmpty,
      reason:
          "This is the walled consumer UI. Internal names and filing "
          "numbers must not appear in it:\n${offences.join("\n")}",
    );
  });
}
