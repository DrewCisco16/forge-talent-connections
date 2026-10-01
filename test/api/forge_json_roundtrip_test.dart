import "dart:convert";

import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/api/forge_json.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/mock_repository.dart";
import "package:forge_talent_connections/models/models.dart";

/// Every model survives a trip to JSON and back, in every scenario.
///
/// Equality is checked on the wire: encode, decode, encode again, and the two
/// strings must match. A field the codec forgets to write, or writes under a
/// different name than it reads, fails here before any backend exists.
void main() {
  for (final DemoScenario scenario in DemoScenario.values) {
    group("round trip in the ${scenario.name} scenario", () {
      final MockForgeRepository repo = MockForgeRepository(scenario);

      void trip<T>(
        String name,
        Future<T> Function() load,
        Map<String, dynamic> Function(T) encode,
        T Function(Map<String, dynamic>) decode,
      ) {
        test(name, () async {
          final T value = await load();
          final String once = jsonEncode(encode(value));
          final T back = decode(jsonDecode(once) as Map<String, dynamic>);
          expect(jsonEncode(encode(back)), once);
        });
      }

      void tripList<T>(
        String name,
        Future<List<T>> Function() load,
        Map<String, dynamic> Function(T) encode,
        T Function(Map<String, dynamic>) decode,
      ) {
        test(name, () async {
          final List<T> values = await load();
          final String once = jsonEncode(
            ForgeJson.wrapItems(values.map(encode).toList()),
          );
          final List<T> back = ForgeJson.items(
            jsonDecode(once) as Map<String, dynamic>,
            decode,
          );
          expect(
            jsonEncode(ForgeJson.wrapItems(back.map(encode).toList())),
            once,
          );
          expect(back.length, values.length);
        });
      }

      trip<UserProfile>(
        "profile",
        repo.loadProfile,
        ForgeJson.profileJson,
        ForgeJson.profile,
      );
      tripList<AvatarOption>(
        "avatars",
        repo.loadAvatars,
        ForgeJson.avatarJson,
        ForgeJson.avatar,
      );
      tripList<ServiceBranch>(
        "branches",
        repo.loadBranches,
        ForgeJson.branchJson,
        ForgeJson.branch,
      );
      trip<ElevatorPitch>(
        "elevator pitch",
        repo.loadElevatorPitch,
        ForgeJson.elevatorPitchJson,
        ForgeJson.elevatorPitch,
      );
      tripList<Opportunity>(
        "opportunities",
        repo.loadOpportunities,
        ForgeJson.opportunityJson,
        ForgeJson.opportunity,
      );
      tripList<Opportunity>(
        "suggested opportunities",
        repo.loadSuggestedOpportunities,
        ForgeJson.opportunityJson,
        ForgeJson.opportunity,
      );
      test("every match suggestion", () async {
        for (final Opportunity o in await repo.loadOpportunities()) {
          final MatchSuggestion s = await repo.loadMatchSuggestion(o.id);
          final String once = jsonEncode(ForgeJson.matchSuggestionJson(s));
          final MatchSuggestion back = ForgeJson.matchSuggestion(
            jsonDecode(once) as Map<String, dynamic>,
          );
          expect(jsonEncode(ForgeJson.matchSuggestionJson(back)), once);
        }
      });
      tripList<Credential>(
        "credentials",
        repo.loadCredentials,
        ForgeJson.credentialJson,
        ForgeJson.credential,
      );
      trip<TrustWalletSummary>(
        "wallet summary",
        repo.loadWalletSummary,
        ForgeJson.walletSummaryJson,
        ForgeJson.walletSummary,
      );
      tripList<Vouch>(
        "vouches",
        repo.loadVouches,
        ForgeJson.vouchJson,
        ForgeJson.vouch,
      );
      trip<ProjectSpace>(
        "project space",
        repo.loadProjectSpace,
        ForgeJson.projectSpaceJson,
        ForgeJson.projectSpace,
      );
      tripList<Story>(
        "stories",
        repo.loadStories,
        ForgeJson.storyJson,
        ForgeJson.story,
      );
      tripList<TalentStory>(
        "talent stories",
        repo.loadTalentStories,
        ForgeJson.talentStoryJson,
        ForgeJson.talentStory,
      );
      tripList<FeedPost>(
        "feed",
        repo.loadFeed,
        ForgeJson.feedPostJson,
        ForgeJson.feedPost,
      );
      trip<ChatThread>(
        "chat thread",
        repo.loadThread,
        ForgeJson.chatThreadJson,
        ForgeJson.chatThread,
      );
      tripList<AppNotification>(
        "notifications",
        repo.loadNotifications,
        ForgeJson.notificationJson,
        ForgeJson.notification,
      );
      tripList<ExportItem>(
        "export queue",
        repo.loadExportQueue,
        ForgeJson.exportItemJson,
        ForgeJson.exportItem,
      );
      trip<IntegrityCertificate>(
        "certificate",
        repo.loadCertificate,
        ForgeJson.certificateJson,
        ForgeJson.certificate,
      );
      tripList<RoadMatch>(
        "roads",
        () => repo.loadRoads("0671"),
        ForgeJson.roadJson,
        ForgeJson.road,
      );
      trip<MembershipStatus>(
        "membership",
        repo.loadMembership,
        ForgeJson.membershipJson,
        ForgeJson.membership,
      );
      trip<AssistantDraft>(
        "portfolio draft",
        repo.loadPortfolioDraft,
        ForgeJson.portfolioDraftJson,
        ForgeJson.portfolioDraft,
      );
      tripList<VerifiedSkill>(
        "verified skills",
        repo.loadVerifiedSkills,
        ForgeJson.verifiedSkillJson,
        ForgeJson.verifiedSkill,
      );
      trip<IntegrityStreak>(
        "streak",
        repo.loadStreak,
        ForgeJson.streakJson,
        ForgeJson.streak,
      );
      tripList<GivenVouch>(
        "given vouches",
        repo.loadGivenVouches,
        ForgeJson.givenVouchJson,
        ForgeJson.givenVouch,
      );
      tripList<SystemDecision>(
        "decisions",
        repo.loadDecisions,
        ForgeJson.decisionJson,
        ForgeJson.decision,
      );
      trip<PitchStudio>(
        "pitch studio",
        repo.loadPitchStudio,
        ForgeJson.pitchStudioJson,
        ForgeJson.pitchStudio,
      );
      trip<RewardsProgram>(
        "rewards",
        repo.loadRewards,
        ForgeJson.rewardsJson,
        ForgeJson.rewards,
      );
      tripList<AssistantExchange>(
        "assistant transcript",
        repo.loadAssistantTranscript,
        ForgeJson.assistantExchangeJson,
        ForgeJson.assistantExchange,
      );
      trip<TalentSignature>(
        "talent signature",
        repo.loadTalentSignature,
        ForgeJson.talentSignatureJson,
        ForgeJson.talentSignature,
      );
    });
  }

  test("a drifted field is a controlled denial, never a raw error", () {
    expect(
      () => ForgeJson.profile(<String, dynamic>{"display_name": 42}),
      throwsA(
        isA<Object>().having(
          (Object e) => e.toString(),
          "denial",
          contains("RESPONSE_NOT_UNDERSTOOD"),
        ),
      ),
    );
    expect(
      () => ForgeJson.credential(<String, dynamic>{
        "id": "c1",
        "title": "x",
        "status": "approved",
      }),
      throwsA(
        isA<Object>().having(
          (Object e) => e.toString(),
          "denial",
          contains("RESPONSE_NOT_UNDERSTOOD"),
        ),
      ),
    );
  });
}
