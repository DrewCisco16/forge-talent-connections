import "verification_status.dart";

/// A credential the person holds, and what checking has established about it.
class Credential {
  const Credential({
    required this.id,
    required this.title,
    required this.status,
    this.identifier,
    this.validThrough,
    this.sealedOn,
    this.failureReason,
  });

  final String id;
  final String title;
  final VerificationStatus status;
  final String? identifier;
  final String? validThrough;
  final String? sealedOn;

  /// Why a check did not pass. Shown to the person rather than hidden.
  final String? failureReason;

  /// The meta line under the title, assembled from whatever is known.
  String? get metaLine {
    final List<String> parts = <String>[
      if (identifier != null) identifier!,
      if (validThrough != null) "valid through $validThrough",
      if (sealedOn != null) "Sealed $sealedOn",
      if (failureReason != null) failureReason!,
    ];
    return parts.isEmpty ? null : parts.join(" · ");
  }
}

/// A piece of work submitted to a project.
class Deliverable {
  const Deliverable({
    required this.id,
    required this.name,
    required this.status,
    this.submittedOn,
    this.failureReason,
  });

  final String id;
  final String name;
  final VerificationStatus status;
  final String? submittedOn;
  final String? failureReason;
}

/// Someone putting their name to another person's work.
class Vouch {
  const Vouch({
    required this.id,
    required this.fromName,
    required this.fromAvatar,
    required this.scope,
    required this.text,
    required this.signedOn,
    this.basis,
    this.basisStatus = VerificationStatus.unverified,
  });

  final String id;
  final String fromName;
  final String fromAvatar;

  /// Skills, Character, or Both.
  final String scope;
  final String text;
  final String signedOn;

  /// What the vouch rests on — a shared verified project outweighs
  /// acquaintance, and the basis is shown on the vouch itself.
  final String? basis;
  final VerificationStatus basisStatus;
}

/// The headline counts on the trust wallet.
///
/// Every number here comes from the backend. None is computed in the UI.
class TrustWalletSummary {
  const TrustWalletSummary({
    required this.deliverables,
    required this.credentials,
    required this.vouches,
  });

  final int deliverables;
  final int credentials;
  final int vouches;
}
