/// The verification outcomes this UI can be asked to render.
///
/// These are states received from the backend, never computed here. The UI
/// renders whatever it is given and decides nothing: there is no client-side
/// verification, scoring, or gating.
///
/// The build guide lists four states and specifies five chips. [unverified] is
/// the reconciling value: screen B4 shows credentials that have not yet been
/// submitted for checking as UNVERIFIED, which is distinct from [pending] (sent,
/// awaiting an outcome) and from [failed] (checked, did not pass).
enum VerificationStatus {
  /// The check passed. The only state that may be presented as trustworthy.
  verified,

  /// Submitted, outcome not yet known. Renders as pending, never as success.
  pending,

  /// Not yet submitted for checking.
  unverified,

  /// Checked and did not pass.
  failed,

  /// Withheld from release. Downstream actions such as export stay blocked.
  locked;

  /// Whether this state may be presented to the user as a proven fact.
  ///
  /// Everything that is not [verified] is not proof. Unknown renders as
  /// pending, never as optimistic success.
  bool get isProven => this == VerificationStatus.verified;

  /// Whether this state blocks a downstream action such as export.
  bool get blocksRelease =>
      this == VerificationStatus.failed || this == VerificationStatus.locked;
}
