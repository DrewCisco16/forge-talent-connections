import "verification_status.dart";

/// How the person stands against the access requirement.
///
/// Joining takes exactly two accountable human vouches. Evidence such as a
/// sealed record informs a reviewer's decision but never replaces either
/// human, and an invitation starts the process without being a vouch.
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

  /// The evidence lane: sealed records a reviewer can examine before
  /// deciding. Evidence supports the two human decisions, never replaces one.
  final String earnedLaneLabel;
  final VerificationStatus earnedLaneStatus;

  /// Whether the backend has opened the gate. Never computed client-side.
  final bool gateOpen;
}

/// One line of an assistant draft, with the verified source it rests on.
class DraftLine {
  const DraftLine({required this.text, required this.sourceLabel});

  final String text;

  /// Where this line comes from - a seal, a vouch, a project outcome.
  final String sourceLabel;
}

/// A claim the assistant declined to make, and the plain-language reason.
class DeclinedClaim {
  const DeclinedClaim({required this.claim, required this.reason});

  final String claim;
  final String reason;
}

/// The assistant's Verified Portfolio draft: only lines with verified sources, plus an
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

/// The state of a request to generate an AI video pitch of the person.
///
/// A product built on verifying identity never ships a likeness it is not
/// sure of: the backend reports how confident it is that the generated
/// likeness is really this person, and below the required line the studio
/// refuses outright. The threshold and the decision are the backend's; the
/// UI only renders them.
class PitchStudio {
  const PitchStudio({
    required this.consentOnFile,
    required this.likenessConfidencePercent,
    required this.requiredConfidencePercent,
    required this.status,
    required this.note,
  });

  final bool consentOnFile;

  /// 0 while the likeness check is still running.
  final int likenessConfidencePercent;
  final int requiredConfidencePercent;
  final VerificationStatus status;
  final String note;
}

/// One strength in the Talent Signature, with the verified evidence behind
/// it. A strength without evidence does not appear here at all, and a
/// strength whose evidence is still checking is shown still checking.
class SignatureStrength {
  const SignatureStrength({
    required this.name,
    required this.evidence,
    required this.status,
  });

  final String name;

  /// The record that proves it - a seal, a checked deliverable, a vouch.
  final String evidence;
  final VerificationStatus status;
}

/// The Talent Signature: a portrait of strengths drawn only from the
/// verified record.
///
/// It is deliberately not a score. It carries no numbers, no rankings, and
/// no guesses about who the person is; [refusals] states out loud what this
/// feature will never do, so the boundary is part of the product.
class TalentSignature {
  const TalentSignature({
    required this.summary,
    required this.strengths,
    required this.refusals,
  });

  /// One plain-language line, assembled from the evidence below it.
  final String summary;
  final List<SignatureStrength> strengths;

  /// What this feature never does, stated as product copy.
  final List<String> refusals;
}

/// One scripted exchange with the AI Assistant.
///
/// The demo transcript is fixture data; in production the assistant runs on
/// Google Cloud Vertex AI behind the product backend, and research results
/// come from real scholarly registries before the model summarises them.
class AssistantExchange {
  const AssistantExchange({
    required this.question,
    required this.answer,
    this.premium = false,
    this.sampleResults = const <String>[],
  });

  final String question;
  final String answer;

  /// True for the paid research capability.
  final bool premium;

  /// Illustrative registry results; clearly labelled samples, never
  /// fabricated citations with invented authors or identifiers.
  final List<String> sampleResults;
}
