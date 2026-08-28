import "verification_status.dart";

/// How the person stands against the two ways into the community.
///
/// Joining takes two vouches — or one vouch plus a sealed verification, so
/// people who arrive without a network can earn their way in on evidence.
/// The backend decides whether the gate is open; this only reports it.
class MembershipStatus {
  const MembershipStatus({
    required this.vouchesReceived,
    required this.vouchesRequired,
    required this.earnedLaneLabel,
    required this.earnedLaneStatus,
    required this.gateOpen,
  });

  final int vouchesReceived;
  final int vouchesRequired;

  /// The evidence-based lane, e.g. "Sealed service record counts as a vouch".
  final String earnedLaneLabel;
  final VerificationStatus earnedLaneStatus;

  /// Whether the backend has opened the gate. Never computed client-side.
  final bool gateOpen;
}

/// One line of an assistant draft, with the verified source it rests on.
class DraftLine {
  const DraftLine({required this.text, required this.sourceLabel});

  final String text;

  /// Where this line comes from — a seal, a vouch, a project outcome.
  final String sourceLabel;
}

/// A claim the assistant declined to make, and the plain-language reason.
class DeclinedClaim {
  const DeclinedClaim({required this.claim, required this.reason});

  final String claim;
  final String reason;
}

/// The assistant's resume draft: only lines with verified sources, plus an
/// explicit list of what it refused to claim and why.
class AssistantDraft {
  const AssistantDraft({required this.lines, required this.declined});

  final List<DraftLine> lines;
  final List<DeclinedClaim> declined;
}

/// A skill demonstrated by verified work, with the work that proves it.
class VerifiedSkill {
  const VerifiedSkill({
    required this.name,
    required this.source,
    required this.status,
  });

  final String name;
  final String source;
  final VerificationStatus status;
}

/// A run of kept commitments. Counts only verified events, never taps.
class IntegrityStreak {
  const IntegrityStreak({
    required this.count,
    required this.label,
    required this.note,
    required this.active,
  });

  final int count;
  final String label;
  final String note;
  final bool active;
}

/// A vouch this person has given. The ledger is public: vouching spends the
/// voucher's own credibility, so it is visible how each name was spent.
class GivenVouch {
  const GivenVouch({
    required this.toName,
    required this.toAvatar,
    required this.basis,
    required this.signedOn,
  });

  final String toName;
  final String toAvatar;
  final String basis;
  final String signedOn;
}

/// A decision the system rendered about this person, stated in plain
/// language, with a human review path. Decisions are never silent.
class SystemDecision {
  const SystemDecision({
    required this.id,
    required this.what,
    required this.why,
    required this.when,
    required this.canRequestReview,
  });

  final String id;
  final String what;
  final String why;
  final String when;
  final bool canRequestReview;
}
