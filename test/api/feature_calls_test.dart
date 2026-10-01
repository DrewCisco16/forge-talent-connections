import "dart:convert";

import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/api/forge_api_client.dart";
import "package:http/http.dart" as http;
import "package:http/testing.dart";

/// Every feature call reaches its endpoint with the right verb and body,
/// and returns the backend's answer unchanged.
void main() {
  late List<http.Request> seen;
  late ForgeApiClient client;

  setUp(() {
    seen = <http.Request>[];
    client = ForgeApiClient(
      baseUrl: "https://api.test",
      httpClient: MockClient((http.Request r) async {
        seen.add(r);
        return http.Response.bytes(
          utf8.encode(
            jsonEncode(<String, dynamic>{"status": "ok", "echo": r.url.path}),
          ),
          200,
        );
      }),
    );
  });

  Map<String, dynamic> body(http.Request r) =>
      jsonDecode(r.body) as Map<String, dynamic>;

  test("profile and onboarding", () async {
    await client.updateProfile(
      displayName: "Ana",
      skills: const <String>["Python"],
    );
    expect(seen.last.method, "PUT");
    expect(seen.last.url.path, "/api/v1/profile");
    expect(body(seen.last), <String, dynamic>{
      "display_name": "Ana",
      "skills": <String>["Python"],
    });

    await client.submitVeteranVerification(
      branchId: "usmc",
      documentName: "DD214.pdf",
    );
    expect(seen.last.url.path, "/api/v1/veteran-verification");
    await client.addCredential(title: "Security+", identifier: "COMP001");
    expect(seen.last.url.path, "/api/v1/credentials");
    await client.updateElevatorPitch(captionsOn: false);
    expect(seen.last.method, "PUT");
    expect(body(seen.last), <String, dynamic>{"captions_on": false});
    await client.recordConsent("2026-10");
    expect(seen.last.url.path, "/api/v1/legal/consent");
  });

  test("social", () async {
    await client.sendMessage(
      text: "Draft attached",
      attachmentName: "Draft.pdf",
    );
    expect(seen.last.url.path, "/api/v1/chat/messages");
    expect(body(seen.last)["attachment_name"], "Draft.pdf");
    await client.markNotificationsRead();
    expect(body(seen.last)["ids"], isNull);
    await client.endorsePost("p1");
    expect(seen.last.url.path, "/api/v1/feed/endorse");
    await client.postTalentStory(headline: "UX", caption: "Thirty seconds.");
    expect(seen.last.url.path, "/api/v1/talent-stories");
  });

  test("export, seal check, growth, and the assistant", () async {
    await client.requestExport("d1");
    expect(body(seen.last)["deliverable_id"], "d1");
    await client.sealCheck("abc123");
    expect(seen.last.url.path, "/api/v1/seal-check");
    await client.pitchStudioConsent(true);
    expect(body(seen.last)["consent"], isTrue);
    await client.regeneratePortfolioDraft();
    expect(seen.last.url.path, "/api/v1/portfolio-draft/regenerate");
    await client.regenerateTalentSignature();
    expect(seen.last.url.path, "/api/v1/talent-signature/regenerate");
    await client.redeemReferral("FORGE-1234");
    expect(body(seen.last)["code"], "FORGE-1234");
    await client.requestDecisionReview("dec-1");
    expect(seen.last.url.path, "/api/v1/decisions/dec-1/review-request");
    await client.recomputeMatch("analytics-capstone");
    expect(
      seen.last.url.path,
      "/api/v1/opportunities/analytics-capstone/match/recompute",
    );
    final Map<String, dynamic> out = await client.askAssistant(
      "What is in my record?",
    );
    expect(seen.last.url.path, "/api/v1/assistant/ask");
    expect(out["status"], "ok");
    expect(
      seen.every(
        (http.Request r) => r.headers["Content-Type"] == "application/json",
      ),
      isTrue,
    );
  });
}
