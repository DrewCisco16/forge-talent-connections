import "verification_status.dart";

/// One points-earning event. Points attach only to verified actions — a
/// vouch that verified, a referred member who joined and verified, a sealed
/// deliverable. The backend awards every point; the UI only reports it.
class RewardEvent {
  const RewardEvent({
    required this.label,
    required this.points,
    required this.status,
    required this.when,
  });

  final String label;
  final int points;

  /// Points count toward the quarter only when verified. Pending events show
  /// as pending; a locked record freezes its points rather than paying out.
  final VerificationStatus status;
  final String when;
}

/// A prize offered for a points period, described by the program's sponsors.
class RewardPrize {
  const RewardPrize({
    required this.title,
    required this.detail,
    required this.valueLabel,
  });

  final String title;
  final String detail;

  /// Stated prize value, e.g. "$1,000+ value". Program copy, not a receipt.
  final String valueLabel;
}

/// One row of the quarter's top standings.
class LeaderEntry {
  const LeaderEntry({
    required this.name,
    required this.points,
    required this.avatar,
  });

  final String name;
  final int points;
  final String avatar;
}

/// The person's standing in the rewards and referral program.
///
/// Every number here is computed by the backend from verified events. The
/// account status is the program's fail-closed switch: a frozen account shows
/// its freeze and the reason, never a payout path that might appear to work.
class RewardsProgram {
  const RewardsProgram({
    required this.quarterLabel,
    required this.quarterEnds,
    required this.pointsVerified,
    required this.pointsPending,
    required this.standingNote,
    required this.membersEarning,
    required this.referralCode,
    required this.referralsJoined,
    required this.referralsPending,
    required this.topThree,
    required this.events,
    required this.quarterlyPrizes,
    required this.yearlyPrize,
    required this.status,
    required this.note,
  });

  final String quarterLabel;
  final String quarterEnds;

  /// Points from events whose checks passed. The only points that count.
  final int pointsVerified;

  /// Points waiting on checks that are still running.
  final int pointsPending;

  /// Relative standing framed as a tier, e.g. "Top 12% this quarter".
  final String standingNote;

  /// How many members earned points this quarter — the community norm.
  final int membersEarning;

  final String referralCode;
  final int referralsJoined;
  final int referralsPending;

  final List<LeaderEntry> topThree;
  final List<RewardEvent> events;
  final List<RewardPrize> quarterlyPrizes;
  final RewardPrize yearlyPrize;

  /// verified = active and eligible; pending = points under verification;
  /// locked = frozen by an integrity hold, eligibility suspended.
  final VerificationStatus status;
  final String note;
}
