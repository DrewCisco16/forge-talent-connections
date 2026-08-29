import "credential.dart";
import "verification_status.dart";

/// A file queued for export, and whether it may leave.
class ExportItem {
  const ExportItem({
    required this.id,
    required this.filename,
    required this.status,
    this.reason,
  });

  final String id;
  final String filename;
  final VerificationStatus status;

  /// Why a file is locked. Always shown; a denial is never silent.
  final String? reason;
}

/// The certificate shown when work is cleared to leave.
class IntegrityCertificate {
  const IntegrityCertificate({
    required this.filename,
    required this.status,
    required this.checkedOn,
    required this.fingerprint,
    required this.deliveredAsCreated,
  });

  final String filename;
  final VerificationStatus status;
  final String checkedOn;
  final String fingerprint;

  /// Whether the file matches what was created.
  final bool deliveredAsCreated;
}

/// A milestone inside a project space.
class Milestone {
  const Milestone({required this.name, required this.status});

  final String name;
  final VerificationStatus status;
}

/// A project workspace with its milestones and submitted work.
class ProjectSpace {
  const ProjectSpace({
    required this.projectName,
    required this.organization,
    required this.milestones,
    required this.deliverables,
    required this.activity,
    this.teamNorms = const <String>[],
    this.checkInPrompt,
  });

  final String projectName;
  final String organization;
  final List<Milestone> milestones;
  final List<Deliverable> deliverables;
  final List<String> activity;

  /// Working agreements the team accepted at kickoff.
  final List<String> teamNorms;

  /// The current private check-in question, if one is open.
  final String? checkInPrompt;
}

/// A suggested civilian role for a military occupation.
///
/// The fit figures are concept placeholders in this build, not model output.
class RoadMatch {
  const RoadMatch({required this.role, required this.fitPercent});

  final String role;
  final int fitPercent;
}
