import "../models/models.dart";

/// The boundary between this UI and whatever serves it.
///
/// Everything the app displays arrives through these interfaces. The UI decides
/// nothing: it does not verify, match, score, or authorise a release. It asks,
/// and renders the answer it is given — including refusals.
///
/// TODO(api): the production implementation lives behind this seam. Swapping
/// the mock for an HTTP client that calls the backend should require no change
/// to any screen. Base URLs arrive via --dart-define; nothing is committed.

/// Reads the signed-in person's profile, avatar choices and pitch.
abstract interface class ProfileRepository {
  Future<UserProfile> loadProfile();
  Future<List<AvatarOption>> loadAvatars();
  Future<List<ServiceBranch>> loadBranches();
  Future<ElevatorPitch> loadElevatorPitch();
}

/// Reads opportunities and the suggestions made against them.
abstract interface class OpportunityRepository {
  Future<List<Opportunity>> loadOpportunities();
  Future<Opportunity> loadOpportunity(String id);

  /// Suggestions for the dashboard. Suggestions only; a person reviews each one.
  Future<List<Opportunity>> loadSuggestedOpportunities();

  /// The suggestion detail for one opportunity.
  Future<MatchSuggestion> loadMatchSuggestion(String opportunityId);
}

/// Reads credentials, deliverables and vouches.
abstract interface class TrustRepository {
  Future<List<Credential>> loadCredentials();
  Future<TrustWalletSummary> loadWalletSummary();
  Future<List<Vouch>> loadVouches();
  Future<ProjectSpace> loadProjectSpace();
}

/// Reads the social surfaces.
abstract interface class SocialRepository {
  Future<List<Story>> loadStories();
  Future<List<FeedPost>> loadFeed();
  Future<ChatThread> loadThread();
  Future<List<AppNotification>> loadNotifications();
}

/// Reads export state.
///
/// Whether work may leave is decided by the backend. This interface reports
/// that decision; it never makes one.
abstract interface class ExportRepository {
  Future<List<ExportItem>> loadExportQueue();
  Future<IntegrityCertificate> loadCertificate();
}

/// Reads the veteran pathway concept data.
abstract interface class PathwayRepository {
  Future<List<PathwayMatch>> loadPathways(String occupationCode);
}

/// Reads membership standing, growth signals, and the decisions the system
/// has rendered about the person.
///
/// The gate, the streaks, the assistant's draft, and every decision are all
/// computed by the backend. This interface reports them; it decides nothing.
abstract interface class GrowthRepository {
  Future<MembershipStatus> loadMembership();
  Future<AssistantDraft> loadResumeDraft();
  Future<List<VerifiedSkill>> loadVerifiedSkills();
  Future<IntegrityStreak> loadStreak();
  Future<List<GivenVouch>> loadGivenVouches();
  Future<List<SystemDecision>> loadDecisions();
}

/// The full surface the app needs.
abstract interface class ForgeRepository
    implements
        ProfileRepository,
        OpportunityRepository,
        TrustRepository,
        SocialRepository,
        ExportRepository,
        PathwayRepository,
        GrowthRepository {}
