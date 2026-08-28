import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/util/linear_search.dart";

/// The brute-force utilities, pinned at their textbook edges: best case
/// (first element), worst case (last element or absent), the multiple-match
/// variant, and the max_value_index scan including ties and the empty list.
void main() {
  group("linearSearchAll", () {
    const List<int> scores = <int>[55, 65, 32, 40, 55];

    test("best case: a hit on the first element", () {
      expect(linearSearchAll(scores, (int v) => v == 55).first, 0);
    });

    test("worst case position: a hit on the last element", () {
      expect(
        linearSearchAll(<int>[1, 2, 3, 4, 9], (int v) => v == 9),
        <int>[4],
      );
    });

    test("multiple matches: every occurrence is returned, in order", () {
      expect(linearSearchAll(scores, (int v) => v == 55), <int>[0, 4]);
    });

    test("value not found: the honest empty result", () {
      expect(linearSearchAll(scores, (int v) => v == 99), isEmpty);
    });

    test("empty list: nothing to scan, nothing found", () {
      expect(linearSearchAll(<int>[], (int v) => true), isEmpty);
    });
  });

  group("indexOfMax", () {
    test("maximum at the front", () {
      expect(indexOfMax(<int>[100, 88, 93], (int v) => v), 0);
    });

    test("maximum in the middle", () {
      expect(indexOfMax(<int>[88, 100, 93], (int v) => v), 1);
    });

    test("maximum at the end — the full N-1 comparison walk", () {
      final List<int> testScores = <int>[
        88, 93, 75, 80, 67, 71, 92, 90, 83, 100,
      ];
      expect(indexOfMax(testScores, (int v) => v), 9);
      expect(testScores[indexOfMax(testScores, (int v) => v)!], 100);
    });

    test("ties resolve to the first occurrence, deterministically", () {
      expect(indexOfMax(<int>[7, 42, 42, 7], (int v) => v), 1);
    });

    test("empty list returns null rather than inventing an answer", () {
      expect(indexOfMax(<int>[], (int v) => v), isNull);
    });
  });
}
