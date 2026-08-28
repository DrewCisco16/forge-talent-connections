import "verification_status.dart";

/// A tag on an opportunity card, with the accent the design assigns it.
enum TechTagTone { gold, green, cyan, violet }

class TechTag {
  const TechTag(this.label, this.tone);

  final String label;
  final TechTagTone tone;
}

/// A sponsored project a person can apply to.
class Opportunity {
  const Opportunity({
    required this.id,
    required this.title,
    required this.organization,
    required this.organizationKind,
    required this.organizationStatus,
    required this.description,
    required this.tags,
    this.pills = const <String>[],
    this.deliverables = const <String>[],
  });

  final String id;
  final String title;
  final String organization;

  /// For instance "University" or "Health system".
  final String organizationKind;

  /// Whether the sponsoring organisation itself is verified.
  final VerificationStatus organizationStatus;
  final String description;
  final List<TechTag> tags;

  /// Meta pills such as Contract / Remote / a rate band.
  final List<String> pills;
  final List<String> deliverables;
}

/// Whether a reason supports or counts against a suggestion.
enum MatchFactorKind { supporting, against }

/// One stated reason behind a suggestion.
class MatchFactor {
  const MatchFactor(this.text, this.kind);

  final String text;
  final MatchFactorKind kind;
}

/// A suggested pairing between a person and an opportunity.
///
/// This is a suggestion produced by the backend and reviewed by a person. The
/// UI never computes a score, never accepts, and never rejects.
class MatchSuggestion {
  const MatchSuggestion({
    required this.opportunityId,
    required this.opportunityTitle,
    required this.score,
    required this.headline,
    required this.factors,
    required this.reviewState,
  });

  final String opportunityId;
  final String opportunityTitle;

  /// 0-100, as received. Fixture value in the demo build.
  final int score;

  /// For instance "Strong match".
  final String headline;
  final List<MatchFactor> factors;

  /// Where this suggestion sits in human review.
  final VerificationStatus reviewState;
}
