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
    this.engagement,
    this.vouchLevel,
    this.evidence = const <String>[],
    this.seatsOpen,
    this.seatsTotal,
    this.reviewerConfirmed,
    this.scopeOnFile,
    this.startWindow,
    this.expiresOn,
    this.qualified,
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

  /// The engagement's nature: paid, academic credit, service, portfolio.
  final String? engagement;

  /// The trust level required to join, stated plainly.
  final String? vouchLevel;

  /// The portable proof a contributor can earn by completing this project.
  final List<String> evidence;

  /// Resourced-seat facts, reported by the backend. Interest-only listings
  /// carry none of these and are never counted as qualified supply.
  final int? seatsOpen;
  final int? seatsTotal;

  /// Whether an accountable reviewer has confirmed capacity for this project.
  final bool? reviewerConfirmed;

  /// Whether a written scope is on file with the sponsor.
  final bool? scopeOnFile;

  /// The stated start window, e.g. "Sep to Oct 2026".
  final String? startWindow;

  /// When this listing expires and stops counting as supply.
  final String? expiresOn;

  /// The backend's own qualified-supply decision: verified sponsor, written
  /// scope, confirmed reviewer, and at least one open seat. Never computed
  /// client-side; the UI renders the served answer.
  final bool? qualified;
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
