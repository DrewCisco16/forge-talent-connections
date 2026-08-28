/// Brute-force search utilities.
///
/// A brute force algorithm solves a problem through exhaustion: it examines
/// every candidate until the answer is found. Linear search is its simplest
/// form — sequentially checking each element of a list against a predicate.
/// Best case O(1) (a hit on the first element), worst case O(N) (a hit on
/// the last element, or no hit at all), average about N/2 comparisons.
///
/// These helpers are presentation-layer only. They filter and rank data the
/// backend has already served — they never verify, match, score, or gate
/// anything. That boundary is the product's, not the algorithm's.
library;

/// Linear search, multiple-match variant.
///
/// Walks the whole list without breaking on the first hit and returns the
/// indices of every element satisfying [matches]. An empty result is the
/// honest "value not found": the caller renders that state explicitly
/// instead of pretending, which is this app's version of raising the error.
List<int> linearSearchAll<T>(List<T> items, bool Function(T item) matches) {
  final List<int> found = <int>[];
  for (int i = 0; i < items.length; i++) {
    if (matches(items[i])) {
      found.add(i);
    }
  }
  return found;
}

/// Brute-force maximum: the classic max_value_index scan.
///
/// Tracks the index of the largest value seen so far and updates it as the
/// walk proceeds. Returns null for an empty list; on ties the first
/// occurrence wins, so the result is deterministic.
int? indexOfMax<T>(List<T> items, num Function(T item) valueOf) {
  if (items.isEmpty) return null;
  int maxIndex = 0;
  for (int i = 1; i < items.length; i++) {
    if (valueOf(items[i]) > valueOf(items[maxIndex])) {
      maxIndex = i;
    }
  }
  return maxIndex;
}
