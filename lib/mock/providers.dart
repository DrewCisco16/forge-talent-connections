// FIXTURE DATA - NOT PRODUCTION TRUTH
//
// Wires the fixture repository into the widget tree. Swapping in the real
// backend means changing `forgeRepositoryProvider` to build the HTTP client;
// no screen needs to change.
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../api/forge_repository.dart";
import "../models/models.dart";
import "fixtures.dart";
import "mock_repository.dart";

/// Which fixture set the demo is serving.
///
/// Changing this re-renders every screen against a different set of outcomes,
/// which is how the pending and denied paths are demonstrated.
final StateProvider<DemoScenario> demoScenarioProvider =
    StateProvider<DemoScenario>((Ref ref) => DemoScenario.verified);

/// The repository the app reads through.
///
/// TODO(api): build the production client here. Everything downstream is
/// already written against the interface, not the mock.
final Provider<ForgeRepository> forgeRepositoryProvider =
    Provider<ForgeRepository>((Ref ref) {
  return MockForgeRepository(ref.watch(demoScenarioProvider));
});

final FutureProvider<UserProfile> profileProvider =
    FutureProvider<UserProfile>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadProfile());

final FutureProvider<List<AvatarOption>> avatarsProvider =
    FutureProvider<List<AvatarOption>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadAvatars());

final FutureProvider<List<ServiceBranch>> branchesProvider =
    FutureProvider<List<ServiceBranch>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadBranches());

final FutureProvider<ElevatorPitch> elevatorPitchProvider =
    FutureProvider<ElevatorPitch>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadElevatorPitch());

final FutureProvider<List<Opportunity>> opportunitiesProvider =
    FutureProvider<List<Opportunity>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadOpportunities());

final FutureProvider<List<Opportunity>> suggestedOpportunitiesProvider =
    FutureProvider<List<Opportunity>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadSuggestedOpportunities());

final FutureProviderFamily<Opportunity, String> opportunityProvider =
    FutureProvider.family<Opportunity, String>((Ref ref, String id) =>
        ref.watch(forgeRepositoryProvider).loadOpportunity(id));

final FutureProviderFamily<MatchSuggestion, String> matchSuggestionProvider =
    FutureProvider.family<MatchSuggestion, String>((Ref ref, String id) =>
        ref.watch(forgeRepositoryProvider).loadMatchSuggestion(id));

final FutureProvider<List<Credential>> credentialsProvider =
    FutureProvider<List<Credential>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadCredentials());

final FutureProvider<TrustWalletSummary> walletSummaryProvider =
    FutureProvider<TrustWalletSummary>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadWalletSummary());

final FutureProvider<List<Vouch>> vouchesProvider =
    FutureProvider<List<Vouch>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadVouches());

final FutureProvider<ProjectSpace> projectSpaceProvider =
    FutureProvider<ProjectSpace>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadProjectSpace());

final FutureProvider<List<Story>> storiesProvider =
    FutureProvider<List<Story>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadStories());

final FutureProvider<List<FeedPost>> feedProvider =
    FutureProvider<List<FeedPost>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadFeed());

final FutureProvider<ChatThread> chatThreadProvider =
    FutureProvider<ChatThread>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadThread());

final FutureProvider<List<AppNotification>> notificationsProvider =
    FutureProvider<List<AppNotification>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadNotifications());

final FutureProvider<List<ExportItem>> exportQueueProvider =
    FutureProvider<List<ExportItem>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadExportQueue());

final FutureProvider<IntegrityCertificate> certificateProvider =
    FutureProvider<IntegrityCertificate>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadCertificate());

final FutureProvider<List<PathwayMatch>> pathwaysProvider =
    FutureProvider<List<PathwayMatch>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadPathways("0651"));

final FutureProvider<MembershipStatus> membershipProvider =
    FutureProvider<MembershipStatus>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadMembership());

final FutureProvider<AssistantDraft> resumeDraftProvider =
    FutureProvider<AssistantDraft>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadResumeDraft());

final FutureProvider<List<VerifiedSkill>> verifiedSkillsProvider =
    FutureProvider<List<VerifiedSkill>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadVerifiedSkills());

final FutureProvider<IntegrityStreak> streakProvider =
    FutureProvider<IntegrityStreak>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadStreak());

final FutureProvider<List<GivenVouch>> givenVouchesProvider =
    FutureProvider<List<GivenVouch>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadGivenVouches());

final FutureProvider<List<SystemDecision>> decisionsProvider =
    FutureProvider<List<SystemDecision>>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadDecisions());

final FutureProvider<PitchStudio> pitchStudioProvider =
    FutureProvider<PitchStudio>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadPitchStudio());

final FutureProvider<RewardsProgram> rewardsProvider =
    FutureProvider<RewardsProgram>((Ref ref) =>
        ref.watch(forgeRepositoryProvider).loadRewards());
