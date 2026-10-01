import "dart:convert";

import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/api/forge_api_client.dart";
import "package:http/http.dart" as http;
import "package:http/testing.dart";

/// The record-change calls carry the backend's answer to the screen
/// unchanged: pending stays pending, and a refusal is a denial with the
/// backend's own words.
void main() {
  ForgeApiClient over(MockClient c) =>
      ForgeApiClient(baseUrl: "https://api.test", httpClient: c);

  test(
    "a vouch is sent to the vouches endpoint and the answer is returned",
    () async {
      late http.Request seen;
      final ForgeApiClient client = over(
        MockClient((http.Request r) async {
          seen = r;
          return http.Response.bytes(
            utf8.encode(
              jsonEncode(<String, dynamic>{
                "status": "recorded",
                "correlation_id": "cor-1",
                "vouch": <String, dynamic>{"basis_status": "verified"},
              }),
            ),
            200,
          );
        }),
      );
      final Map<String, dynamic> out = await client.giveVouch(
        toUser: "bob",
        scope: "Skills",
        text: "Shipped the outline on time.",
        basis: "Employment Law Presentation",
      );
      expect(seen.method, "POST");
      expect(seen.url.path, "/api/v1/vouches");
      expect(jsonDecode(seen.body)["to_user"], "bob");
      expect(out["status"], "recorded");
      expect(
        (out["vouch"] as Map<String, dynamic>)["basis_status"],
        "verified",
      );
    },
  );

  test("applying never reports success it was not given", () async {
    final ForgeApiClient client = over(
      MockClient(
        (http.Request r) async => http.Response(
          jsonEncode(<String, dynamic>{
            "status": "pending",
            "correlation_id": "cor-2",
          }),
          200,
        ),
      ),
    );
    final Map<String, dynamic> out = await client.applyToOpportunity(
      "analytics-capstone",
    );
    expect(out["status"], "pending");
  });

  test("a self-vouch refusal arrives as the backend's denial", () async {
    final ForgeApiClient client = over(
      MockClient(
        (http.Request r) async => http.Response(
          jsonEncode(<String, dynamic>{
            "status": "denied",
            "code": "SELF_VOUCH",
            "message": "You cannot vouch for yourself. Nothing was changed.",
            "next_step": "Ask a collaborator who has worked with you.",
            "retryable": false,
          }),
          403,
        ),
      ),
    );
    await expectLater(
      client.giveVouch(toUser: "me", scope: "Skills", text: "x"),
      throwsA(
        isA<ForgeDenial>()
            .having((ForgeDenial d) => d.code, "code", "SELF_VOUCH")
            .having(
              (ForgeDenial d) => d.message,
              "message",
              contains("Nothing was changed"),
            ),
      ),
    );
  });

  test("submitting work when changes are off is an honest denial", () async {
    final ForgeApiClient client = over(
      MockClient(
        (http.Request r) async => http.Response(
          jsonEncode(<String, dynamic>{
            "status": "denied",
            "code": "SERVICE_UNAVAILABLE",
            "message": "Changes are not enabled in this environment. Nothing was changed.",
            "next_step": "Try again later.",
            "retryable": false,
          }),
          503,
        ),
      ),
    );
    await expectLater(
      client.submitDeliverable("Final_Deck_v3.pdf"),
      throwsA(
        isA<ForgeDenial>().having(
          (ForgeDenial d) => d.httpStatus,
          "status",
          503,
        ),
      ),
    );
  });
}
