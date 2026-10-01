import "dart:convert";

import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/api/forge_api_client.dart";
import "package:forge_talent_connections/api/forge_json.dart";
import "package:forge_talent_connections/api/http_forge_repository.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/mock_repository.dart";
import "package:forge_talent_connections/models/models.dart";
import "package:http/http.dart" as http;
import "package:http/testing.dart";

/// The live repository against a fake backend that serves the exported
/// fixtures. Proves two things: every method reads its endpoint and decodes
/// the wire format, and every failure mode is a denial the screens already
/// know how to render.
void main() {
  const MockForgeRepository source = MockForgeRepository(DemoScenario.verified);

  /// A backend that answers every read endpoint from the fixtures.
  Future<Map<String, Map<String, dynamic>>> seed() async {
    final Map<String, Map<String, dynamic>> routes =
        <String, Map<String, dynamic>>{};
    List<Map<String, dynamic>> many<T>(
      List<T> xs,
      Map<String, dynamic> Function(T) f,
    ) => xs.map(f).toList();

    routes[HttpForgeRepository.profilePath] = ForgeJson.profileJson(
      await source.loadProfile(),
    );
    routes[HttpForgeRepository.avatarsPath] = ForgeJson.wrapItems(
      many(await source.loadAvatars(), ForgeJson.avatarJson),
    );
    routes[HttpForgeRepository.branchesPath] = ForgeJson.wrapItems(
      many(await source.loadBranches(), ForgeJson.branchJson),
    );
    routes[HttpForgeRepository.elevatorPitchPath] = ForgeJson.elevatorPitchJson(
      await source.loadElevatorPitch(),
    );
    final List<Opportunity> ops = await source.loadOpportunities();
    routes[HttpForgeRepository.opportunitiesPath] = ForgeJson.wrapItems(
      many(ops, ForgeJson.opportunityJson),
    );
    routes[HttpForgeRepository.suggestedPath] = ForgeJson.wrapItems(
      many(
        await source.loadSuggestedOpportunities(),
        ForgeJson.opportunityJson,
      ),
    );
    for (final Opportunity o in ops) {
      routes[HttpForgeRepository.opportunityPath(o.id)] =
          ForgeJson.opportunityJson(o);
      routes[HttpForgeRepository.matchPath(o.id)] =
          ForgeJson.matchSuggestionJson(await source.loadMatchSuggestion(o.id));
    }
    routes[HttpForgeRepository.credentialsPath] = ForgeJson.wrapItems(
      many(await source.loadCredentials(), ForgeJson.credentialJson),
    );
    routes[HttpForgeRepository.walletPath] = ForgeJson.walletSummaryJson(
      await source.loadWalletSummary(),
    );
    routes[HttpForgeRepository.vouchesPath] = ForgeJson.wrapItems(
      many(await source.loadVouches(), ForgeJson.vouchJson),
    );
    routes[HttpForgeRepository.projectSpacePath] = ForgeJson.projectSpaceJson(
      await source.loadProjectSpace(),
    );
    routes[HttpForgeRepository.storiesPath] = ForgeJson.wrapItems(
      many(await source.loadStories(), ForgeJson.storyJson),
    );
    routes[HttpForgeRepository.talentStoriesPath] = ForgeJson.wrapItems(
      many(await source.loadTalentStories(), ForgeJson.talentStoryJson),
    );
    routes[HttpForgeRepository.feedPath] = ForgeJson.wrapItems(
      many(await source.loadFeed(), ForgeJson.feedPostJson),
    );
    routes[HttpForgeRepository.chatThreadPath] = ForgeJson.chatThreadJson(
      await source.loadThread(),
    );
    routes[HttpForgeRepository.notificationsPath] = ForgeJson.wrapItems(
      many(await source.loadNotifications(), ForgeJson.notificationJson),
    );
    routes[HttpForgeRepository.exportQueuePath] = ForgeJson.wrapItems(
      many(await source.loadExportQueue(), ForgeJson.exportItemJson),
    );
    routes[HttpForgeRepository.certificatePath] = ForgeJson.certificateJson(
      await source.loadCertificate(),
    );
    routes["${HttpForgeRepository.roadsPath}?occupation=0671"] =
        ForgeJson.wrapItems(
          many(await source.loadRoads("0671"), ForgeJson.roadJson),
        );
    routes[HttpForgeRepository.membershipPath] = ForgeJson.membershipJson(
      await source.loadMembership(),
    );
    routes[HttpForgeRepository.portfolioDraftPath] =
        ForgeJson.portfolioDraftJson(await source.loadPortfolioDraft());
    routes[HttpForgeRepository.verifiedSkillsPath] = ForgeJson.wrapItems(
      many(await source.loadVerifiedSkills(), ForgeJson.verifiedSkillJson),
    );
    routes[HttpForgeRepository.streakPath] = ForgeJson.streakJson(
      await source.loadStreak(),
    );
    routes[HttpForgeRepository.givenVouchesPath] = ForgeJson.wrapItems(
      many(await source.loadGivenVouches(), ForgeJson.givenVouchJson),
    );
    routes[HttpForgeRepository.decisionsPath] = ForgeJson.wrapItems(
      many(await source.loadDecisions(), ForgeJson.decisionJson),
    );
    routes[HttpForgeRepository.pitchStudioPath] = ForgeJson.pitchStudioJson(
      await source.loadPitchStudio(),
    );
    routes[HttpForgeRepository.rewardsPath] = ForgeJson.rewardsJson(
      await source.loadRewards(),
    );
    routes[HttpForgeRepository.assistantTranscriptPath] = ForgeJson.wrapItems(
      many(
        await source.loadAssistantTranscript(),
        ForgeJson.assistantExchangeJson,
      ),
    );
    routes[HttpForgeRepository.talentSignaturePath] =
        ForgeJson.talentSignatureJson(await source.loadTalentSignature());
    return routes;
  }

  HttpForgeRepository repoOver(MockClient client) => HttpForgeRepository(
    ForgeApiClient(baseUrl: "https://api.test", httpClient: client),
  );

  test("every repository method reads its endpoint and decodes", () async {
    final Map<String, Map<String, dynamic>> routes = await seed();
    final List<String> hits = <String>[];
    final MockClient client = MockClient((http.Request r) async {
      final String key = r.url.path + (r.url.hasQuery ? "?${r.url.query}" : "");
      hits.add(key);
      final Map<String, dynamic>? body = routes[key];
      if (body == null) {
        return http.Response(
          jsonEncode(<String, dynamic>{
            "status": "denied",
            "code": "NOT_FOUND",
            "message": "No such record.",
            "next_step": "Check the address.",
            "retryable": false,
          }),
          404,
        );
      }
      // Bytes, like a real server: the records contain a middle dot and
      // curly quotes, which only survive as UTF-8.
      return http.Response.bytes(utf8.encode(jsonEncode(body)), 200);
    });
    final HttpForgeRepository repo = repoOver(client);

    expect((await repo.loadProfile()).displayName, "Drew Cisco");
    expect(await repo.loadAvatars(), isNotEmpty);
    expect(await repo.loadBranches(), isNotEmpty);
    expect((await repo.loadElevatorPitch()).isAiPresented, isTrue);
    final List<Opportunity> ops = await repo.loadOpportunities();
    expect(ops, isNotEmpty);
    expect((await repo.loadOpportunity(ops.first.id)).id, ops.first.id);
    expect(await repo.loadSuggestedOpportunities(), isNotEmpty);
    expect(
      (await repo.loadMatchSuggestion(ops.first.id)).opportunityId,
      ops.first.id,
    );
    expect(await repo.loadCredentials(), isNotEmpty);
    expect((await repo.loadWalletSummary()).vouches, greaterThanOrEqualTo(0));
    expect(await repo.loadVouches(), isNotEmpty);
    expect((await repo.loadProjectSpace()).milestones, isNotEmpty);
    expect(await repo.loadStories(), isNotEmpty);
    expect(await repo.loadTalentStories(), isNotEmpty);
    expect(await repo.loadFeed(), isNotEmpty);
    expect((await repo.loadThread()).messages, isNotEmpty);
    expect(await repo.loadNotifications(), isNotEmpty);
    expect(await repo.loadExportQueue(), isNotEmpty);
    expect((await repo.loadCertificate()).fingerprint, isNotEmpty);
    expect(await repo.loadRoads("0671"), isNotEmpty);
    expect((await repo.loadMembership()).vouchesRequired, 2);
    expect((await repo.loadPortfolioDraft()).lines, isNotEmpty);
    expect(await repo.loadVerifiedSkills(), isNotEmpty);
    expect((await repo.loadStreak()).label, isNotEmpty);
    expect(await repo.loadGivenVouches(), isNotEmpty);
    expect(await repo.loadDecisions(), isNotEmpty);
    expect(
      (await repo.loadPitchStudio()).requiredConfidencePercent,
      isPositive,
    );
    expect((await repo.loadRewards()).referralCode, isNotEmpty);
    expect(await repo.loadAssistantTranscript(), isNotEmpty);
    expect((await repo.loadTalentSignature()).strengths, isNotEmpty);

    // Every request hit a route the fake backend knows: no stray paths, and
    // one request per repository method (the per-id routes are exercised
    // for the first opportunity only).
    expect(routes.keys.toSet().containsAll(hits), isTrue, reason: "$hits");
    expect(hits.length, 30);
  });

  test("a backend denial reaches the screen as a denial", () async {
    final MockClient client = MockClient(
      (http.Request r) async => http.Response(
        jsonEncode(<String, dynamic>{
          "status": "denied",
          "code": "SERVICE_UNAVAILABLE",
          "message": "The record service is unavailable. Nothing was changed.",
          "next_step": "Try again in a few minutes.",
          "retryable": true,
        }),
        503,
      ),
    );
    await expectLater(
      repoOver(client).loadProfile(),
      throwsA(
        isA<ForgeDenial>()
            .having((ForgeDenial d) => d.code, "code", "SERVICE_UNAVAILABLE")
            .having((ForgeDenial d) => d.retryable, "retryable", isTrue)
            .having((ForgeDenial d) => d.httpStatus, "status", 503),
      ),
    );
  });

  test("a 200 with the wrong shape is RESPONSE_NOT_UNDERSTOOD", () async {
    final MockClient client = MockClient(
      (http.Request r) async =>
          http.Response(jsonEncode(<String, dynamic>{"display_name": 7}), 200),
    );
    await expectLater(
      repoOver(client).loadProfile(),
      throwsA(
        isA<ForgeDenial>().having(
          (ForgeDenial d) => d.code,
          "code",
          "RESPONSE_NOT_UNDERSTOOD",
        ),
      ),
    );
  });

  test("a network failure is a retryable transport denial", () async {
    final MockClient client = MockClient(
      (http.Request r) async => throw http.ClientException("offline"),
    );
    await expectLater(
      repoOver(client).loadFeed(),
      throwsA(
        isA<ForgeDenial>()
            .having((ForgeDenial d) => d.code, "code", "SERVICE_UNAVAILABLE")
            .having((ForgeDenial d) => d.httpStatus, "status", 0),
      ),
    );
  });

  test("non-JSON on a 200 is RESPONSE_NOT_UNDERSTOOD, never a crash", () async {
    final MockClient client = MockClient(
      (http.Request r) async => http.Response("<html>maintenance</html>", 200),
    );
    await expectLater(
      repoOver(client).loadRewards(),
      throwsA(
        isA<ForgeDenial>().having(
          (ForgeDenial d) => d.code,
          "code",
          "RESPONSE_NOT_UNDERSTOOD",
        ),
      ),
    );
  });
}
