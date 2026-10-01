import "../models/models.dart";
import "forge_api_client.dart";
import "forge_json.dart";
import "forge_repository.dart";

/// The production repository: every read the app makes, served by the
/// product backend over HTTPS.
///
/// Screens never see this class. They read providers, which read the
/// [ForgeRepository] interface, and this is one implementation of it. Every
/// failure (transport, timeout, non-2xx, unexpected shape) surfaces as a
/// [ForgeDenial], which the screens already render as an honest pending or
/// denied state. Nothing here computes, scores, verifies, or decides.
class HttpForgeRepository implements ForgeRepository {
  HttpForgeRepository(this._client);

  final ForgeApiClient _client;

  /// Read endpoints. One path per repository method; lists are wrapped as
  /// `{"items": [...]}`. The backend's README carries the same table.
  static const String profilePath = "/api/v1/profile";
  static const String avatarsPath = "/api/v1/avatars";
  static const String branchesPath = "/api/v1/branches";
  static const String elevatorPitchPath = "/api/v1/elevator-pitch";
  static const String opportunitiesPath = "/api/v1/opportunities";
  static const String suggestedPath = "/api/v1/opportunities/suggested";
  static const String credentialsPath = "/api/v1/credentials";
  static const String walletPath = "/api/v1/trust-wallet";
  static const String vouchesPath = "/api/v1/vouches";
  static const String projectSpacePath = "/api/v1/project-space";
  static const String storiesPath = "/api/v1/stories";
  static const String talentStoriesPath = "/api/v1/talent-stories";
  static const String feedPath = "/api/v1/feed";
  static const String chatThreadPath = "/api/v1/chat/thread";
  static const String notificationsPath = "/api/v1/notifications";
  static const String exportQueuePath = "/api/v1/export/queue";
  static const String certificatePath = "/api/v1/export/certificate";
  static const String roadsPath = "/api/v1/roads";
  static const String membershipPath = "/api/v1/membership";
  static const String portfolioDraftPath = "/api/v1/portfolio-draft";
  static const String verifiedSkillsPath = "/api/v1/verified-skills";
  static const String streakPath = "/api/v1/streak";
  static const String givenVouchesPath = "/api/v1/given-vouches";
  static const String decisionsPath = "/api/v1/decisions";
  static const String pitchStudioPath = "/api/v1/pitch-studio";
  static const String rewardsPath = "/api/v1/rewards";
  static const String assistantTranscriptPath = "/api/v1/assistant/transcript";
  static const String talentSignaturePath = "/api/v1/talent-signature";

  static String opportunityPath(String id) =>
      "$opportunitiesPath/${Uri.encodeComponent(id)}";
  static String matchPath(String id) => "${opportunityPath(id)}/match";

  Future<Map<String, dynamic>> _get(String path) => _client.get(path);

  // ------------------------------------------------------------ profile

  @override
  Future<UserProfile> loadProfile() async =>
      ForgeJson.profile(await _get(profilePath));

  @override
  Future<List<AvatarOption>> loadAvatars() async =>
      ForgeJson.items(await _get(avatarsPath), ForgeJson.avatar);

  @override
  Future<List<ServiceBranch>> loadBranches() async =>
      ForgeJson.items(await _get(branchesPath), ForgeJson.branch);

  @override
  Future<ElevatorPitch> loadElevatorPitch() async =>
      ForgeJson.elevatorPitch(await _get(elevatorPitchPath));

  // ------------------------------------------------------------ opportunity

  @override
  Future<List<Opportunity>> loadOpportunities() async =>
      ForgeJson.items(await _get(opportunitiesPath), ForgeJson.opportunity);

  @override
  Future<Opportunity> loadOpportunity(String id) async =>
      ForgeJson.opportunity(await _get(opportunityPath(id)));

  @override
  Future<List<Opportunity>> loadSuggestedOpportunities() async =>
      ForgeJson.items(await _get(suggestedPath), ForgeJson.opportunity);

  @override
  Future<MatchSuggestion> loadMatchSuggestion(String opportunityId) async =>
      ForgeJson.matchSuggestion(await _get(matchPath(opportunityId)));

  // ------------------------------------------------------------ trust

  @override
  Future<List<Credential>> loadCredentials() async =>
      ForgeJson.items(await _get(credentialsPath), ForgeJson.credential);

  @override
  Future<TrustWalletSummary> loadWalletSummary() async =>
      ForgeJson.walletSummary(await _get(walletPath));

  @override
  Future<List<Vouch>> loadVouches() async =>
      ForgeJson.items(await _get(vouchesPath), ForgeJson.vouch);

  @override
  Future<ProjectSpace> loadProjectSpace() async =>
      ForgeJson.projectSpace(await _get(projectSpacePath));

  // ------------------------------------------------------------ social

  @override
  Future<List<Story>> loadStories() async =>
      ForgeJson.items(await _get(storiesPath), ForgeJson.story);

  @override
  Future<List<TalentStory>> loadTalentStories() async =>
      ForgeJson.items(await _get(talentStoriesPath), ForgeJson.talentStory);

  @override
  Future<List<FeedPost>> loadFeed() async =>
      ForgeJson.items(await _get(feedPath), ForgeJson.feedPost);

  @override
  Future<ChatThread> loadThread() async =>
      ForgeJson.chatThread(await _get(chatThreadPath));

  @override
  Future<List<AppNotification>> loadNotifications() async =>
      ForgeJson.items(await _get(notificationsPath), ForgeJson.notification);

  // ------------------------------------------------------------ export

  @override
  Future<List<ExportItem>> loadExportQueue() async =>
      ForgeJson.items(await _get(exportQueuePath), ForgeJson.exportItem);

  @override
  Future<IntegrityCertificate> loadCertificate() async =>
      ForgeJson.certificate(await _get(certificatePath));

  // ------------------------------------------------------------ roads

  @override
  Future<List<RoadMatch>> loadRoads(String occupationCode) async =>
      ForgeJson.items(
        await _get(
          "$roadsPath?occupation=${Uri.encodeQueryComponent(occupationCode)}",
        ),
        ForgeJson.road,
      );

  // ------------------------------------------------------------ growth

  @override
  Future<MembershipStatus> loadMembership() async =>
      ForgeJson.membership(await _get(membershipPath));

  @override
  Future<AssistantDraft> loadPortfolioDraft() async =>
      ForgeJson.portfolioDraft(await _get(portfolioDraftPath));

  @override
  Future<List<VerifiedSkill>> loadVerifiedSkills() async =>
      ForgeJson.items(await _get(verifiedSkillsPath), ForgeJson.verifiedSkill);

  @override
  Future<IntegrityStreak> loadStreak() async =>
      ForgeJson.streak(await _get(streakPath));

  @override
  Future<List<GivenVouch>> loadGivenVouches() async =>
      ForgeJson.items(await _get(givenVouchesPath), ForgeJson.givenVouch);

  @override
  Future<List<SystemDecision>> loadDecisions() async =>
      ForgeJson.items(await _get(decisionsPath), ForgeJson.decision);

  @override
  Future<PitchStudio> loadPitchStudio() async =>
      ForgeJson.pitchStudio(await _get(pitchStudioPath));

  @override
  Future<RewardsProgram> loadRewards() async =>
      ForgeJson.rewards(await _get(rewardsPath));

  @override
  Future<List<AssistantExchange>> loadAssistantTranscript() async =>
      ForgeJson.items(
        await _get(assistantTranscriptPath),
        ForgeJson.assistantExchange,
      );

  @override
  Future<TalentSignature> loadTalentSignature() async =>
      ForgeJson.talentSignature(await _get(talentSignaturePath));
}
