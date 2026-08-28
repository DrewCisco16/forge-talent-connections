import "verification_status.dart";

/// Which kind of account the visitor says they are, chosen on the splash screen.
enum ForgeRole {
  talent("Talent", "Show verified work and get matched"),
  opportunity("Opportunity", "Post projects and onboard proven people"),
  veteran("Veteran", "Translate your service into project work");

  const ForgeRole(this.label, this.blurb);

  final String label;
  final String blurb;
}

/// One selectable avatar in the A3 grid.
class AvatarOption {
  const AvatarOption({required this.id, required this.asset});

  final String id;

  /// Bundled artwork path.
  final String asset;
}

/// A branch of service shown on the verification screen.
///
/// Branch colours are authentic service colours and are exempt from theming.
class ServiceBranch {
  const ServiceBranch({
    required this.id,
    required this.name,
    required this.shortName,
    required this.motto,
  });

  final String id;
  final String name;
  final String shortName;
  final String motto;
}

/// The signed-in person's profile as the backend reports it.
class UserProfile {
  const UserProfile({
    required this.displayName,
    required this.skills,
    required this.about,
    required this.avatarAsset,
    required this.completionPercent,
    required this.serviceRecord,
  });

  final String displayName;
  final List<String> skills;
  final String about;
  final String? avatarAsset;

  /// Completion as reported by the backend. Never computed here.
  final int completionPercent;

  /// The state of the sealed service record, if the person is a veteran.
  final VerificationStatus serviceRecord;
}

/// The elevator pitch video and whether it was AI-presented.
class ElevatorPitch {
  const ElevatorPitch({
    required this.durationSeconds,
    required this.positionSeconds,
    required this.captionsOn,
    required this.isAiPresented,
    this.transcript,
  });

  final int durationSeconds;
  final int positionSeconds;
  final bool captionsOn;

  /// Drives the visible AI-generated label wherever this pitch plays.
  final bool isAiPresented;
  final String? transcript;
}
