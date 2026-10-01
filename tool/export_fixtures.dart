// Exports the fixture data as the backend's seed, in the exact wire format
// the app reads, so the first live backend answers with the same records the
// demo has always shown.
//
// Run from the repository root:
//   dart run tool/export_fixtures.dart <output-directory>
//
// Writes one JSON file per endpoint for the verified scenario. The output
// directory is not committed here; it ships with the backend.
import "dart:convert";
import "dart:io";

import "package:forge_talent_connections/api/forge_json.dart";
import "package:forge_talent_connections/api/http_forge_repository.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/mock_repository.dart";
import "package:forge_talent_connections/models/models.dart";

Future<void> main(List<String> args) async {
  if (args.isEmpty) {
    stderr.writeln("usage: dart run tool/export_fixtures.dart <output-dir>");
    exit(64);
  }
  final Directory out = Directory(args.first)..createSync(recursive: true);
  final MockForgeRepository repo = const MockForgeRepository(
    DemoScenario.verified,
  );
  const JsonEncoder enc = JsonEncoder.withIndent("  ");

  String fileFor(String path) =>
      "${path.replaceFirst("/api/v1/", "").replaceAll("/", "__").replaceAll("?", "__")}.json";

  Future<void> write(String path, Map<String, dynamic> body) async {
    final File f = File("${out.path}/${fileFor(path)}");
    await f.writeAsString("${enc.convert(body)}\n");
    stdout.writeln("wrote ${f.path}");
  }

  List<Map<String, dynamic>> many<T>(
    List<T> xs,
    Map<String, dynamic> Function(T) f,
  ) => xs.map(f).toList();

  await write(
    HttpForgeRepository.profilePath,
    ForgeJson.profileJson(await repo.loadProfile()),
  );
  await write(
    HttpForgeRepository.avatarsPath,
    ForgeJson.wrapItems(many(await repo.loadAvatars(), ForgeJson.avatarJson)),
  );
  await write(
    HttpForgeRepository.branchesPath,
    ForgeJson.wrapItems(many(await repo.loadBranches(), ForgeJson.branchJson)),
  );
  await write(
    HttpForgeRepository.elevatorPitchPath,
    ForgeJson.elevatorPitchJson(await repo.loadElevatorPitch()),
  );

  final List<Opportunity> opportunities = await repo.loadOpportunities();
  await write(
    HttpForgeRepository.opportunitiesPath,
    ForgeJson.wrapItems(many(opportunities, ForgeJson.opportunityJson)),
  );
  await write(
    HttpForgeRepository.suggestedPath,
    ForgeJson.wrapItems(
      many(await repo.loadSuggestedOpportunities(), ForgeJson.opportunityJson),
    ),
  );
  for (final Opportunity o in opportunities) {
    await write(
      HttpForgeRepository.opportunityPath(o.id),
      ForgeJson.opportunityJson(o),
    );
    await write(
      HttpForgeRepository.matchPath(o.id),
      ForgeJson.matchSuggestionJson(await repo.loadMatchSuggestion(o.id)),
    );
  }

  await write(
    HttpForgeRepository.credentialsPath,
    ForgeJson.wrapItems(
      many(await repo.loadCredentials(), ForgeJson.credentialJson),
    ),
  );
  await write(
    HttpForgeRepository.walletPath,
    ForgeJson.walletSummaryJson(await repo.loadWalletSummary()),
  );
  await write(
    HttpForgeRepository.vouchesPath,
    ForgeJson.wrapItems(many(await repo.loadVouches(), ForgeJson.vouchJson)),
  );
  await write(
    HttpForgeRepository.projectSpacePath,
    ForgeJson.projectSpaceJson(await repo.loadProjectSpace()),
  );

  await write(
    HttpForgeRepository.storiesPath,
    ForgeJson.wrapItems(many(await repo.loadStories(), ForgeJson.storyJson)),
  );
  await write(
    HttpForgeRepository.talentStoriesPath,
    ForgeJson.wrapItems(
      many(await repo.loadTalentStories(), ForgeJson.talentStoryJson),
    ),
  );
  await write(
    HttpForgeRepository.feedPath,
    ForgeJson.wrapItems(many(await repo.loadFeed(), ForgeJson.feedPostJson)),
  );
  await write(
    HttpForgeRepository.chatThreadPath,
    ForgeJson.chatThreadJson(await repo.loadThread()),
  );
  await write(
    HttpForgeRepository.notificationsPath,
    ForgeJson.wrapItems(
      many(await repo.loadNotifications(), ForgeJson.notificationJson),
    ),
  );

  await write(
    HttpForgeRepository.exportQueuePath,
    ForgeJson.wrapItems(
      many(await repo.loadExportQueue(), ForgeJson.exportItemJson),
    ),
  );
  await write(
    HttpForgeRepository.certificatePath,
    ForgeJson.certificateJson(await repo.loadCertificate()),
  );
  await write(
    HttpForgeRepository.roadsPath,
    ForgeJson.wrapItems(many(await repo.loadRoads("0671"), ForgeJson.roadJson)),
  );

  await write(
    HttpForgeRepository.membershipPath,
    ForgeJson.membershipJson(await repo.loadMembership()),
  );
  await write(
    HttpForgeRepository.portfolioDraftPath,
    ForgeJson.portfolioDraftJson(await repo.loadPortfolioDraft()),
  );
  await write(
    HttpForgeRepository.verifiedSkillsPath,
    ForgeJson.wrapItems(
      many(await repo.loadVerifiedSkills(), ForgeJson.verifiedSkillJson),
    ),
  );
  await write(
    HttpForgeRepository.streakPath,
    ForgeJson.streakJson(await repo.loadStreak()),
  );
  await write(
    HttpForgeRepository.givenVouchesPath,
    ForgeJson.wrapItems(
      many(await repo.loadGivenVouches(), ForgeJson.givenVouchJson),
    ),
  );
  await write(
    HttpForgeRepository.decisionsPath,
    ForgeJson.wrapItems(
      many(await repo.loadDecisions(), ForgeJson.decisionJson),
    ),
  );
  await write(
    HttpForgeRepository.pitchStudioPath,
    ForgeJson.pitchStudioJson(await repo.loadPitchStudio()),
  );
  await write(
    HttpForgeRepository.rewardsPath,
    ForgeJson.rewardsJson(await repo.loadRewards()),
  );
  await write(
    HttpForgeRepository.assistantTranscriptPath,
    ForgeJson.wrapItems(
      many(
        await repo.loadAssistantTranscript(),
        ForgeJson.assistantExchangeJson,
      ),
    ),
  );
  await write(
    HttpForgeRepository.talentSignaturePath,
    ForgeJson.talentSignatureJson(await repo.loadTalentSignature()),
  );
}
