import "dart:convert";

import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/api/forge_api_client.dart";
import "package:http/http.dart" as http;
import "package:http/testing.dart";

/// The live client fails closed on every path: transport errors, non-2xx
/// statuses, denied bodies, and unrecognised shapes all resolve to a denial,
/// writes are never retried, and health never answers an optimistic true.
void main() {
  ForgeApiClient clientWith(MockClient mock) =>
      ForgeApiClient(baseUrl: "https://api.example.test", httpClient: mock);

  test("constructing without a base URL fails at startup", () {
    expect(() => ForgeApiClient(baseUrl: ""), throwsA(isA<ForgeConfigError>()));
  });

  test("a transport error is a denial, and the write is not retried", () async {
    int calls = 0;
    final ForgeApiClient client = clientWith(
      MockClient((http.Request req) async {
        calls += 1;
        throw http.ClientException("connection refused");
      }),
    );
    await expectLater(
      client.evaluate(targetKey: "k", payload: <String, dynamic>{}),
      throwsA(
        isA<ForgeDenial>().having(
          (ForgeDenial d) => d.code,
          "code",
          "SERVICE_UNAVAILABLE",
        ),
      ),
    );
    expect(calls, 1, reason: "a non-idempotent POST must never be retried");
  });

  test("a denied body surfaces its consumer-safe strings verbatim", () async {
    final ForgeApiClient client = clientWith(
      MockClient(
        (http.Request req) async => http.Response(
          jsonEncode(<String, dynamic>{
            "status": "denied",
            "code": "REVIEW_REQUIRED",
            "message": "A reviewer has to look at this first.",
            "next_step": "You will be notified.",
            "retryable": false,
          }),
          409,
        ),
      ),
    );
    await expectLater(
      client.governedWrite(
        requestedBy: "drew",
        purpose: "demo",
        targetKey: "k",
        payload: <String, dynamic>{},
      ),
      throwsA(
        isA<ForgeDenial>()
            .having((ForgeDenial d) => d.needsHumanReview, "review", true)
            .having(
              (ForgeDenial d) => d.message,
              "message",
              "A reviewer has to look at this first.",
            ),
      ),
    );
  });

  test("an unrecognised response shape is a denial, never a success", () async {
    final ForgeApiClient client = clientWith(
      MockClient((http.Request req) async => http.Response("<html>", 200)),
    );
    await expectLater(
      client.evaluate(targetKey: "k", payload: <String, dynamic>{}),
      throwsA(
        isA<ForgeDenial>().having(
          (ForgeDenial d) => d.code,
          "code",
          "RESPONSE_NOT_UNDERSTOOD",
        ),
      ),
    );
  });

  test("health is false on any failure and true only on a real ok", () async {
    final ForgeApiClient down = clientWith(
      MockClient((http.Request req) async => http.Response("oops", 500)),
    );
    expect(await down.isHealthy(), isFalse);

    final ForgeApiClient broken = clientWith(
      MockClient((http.Request req) async {
        throw http.ClientException("no route");
      }),
    );
    expect(await broken.isHealthy(), isFalse);

    final ForgeApiClient up = clientWith(
      MockClient(
        (http.Request req) async =>
            http.Response(jsonEncode(<String, String>{"status": "ok"}), 200),
      ),
    );
    expect(await up.isHealthy(), isTrue);
  });

  test("a successful write returns the correlation and record keys", () async {
    final ForgeApiClient client = clientWith(
      MockClient(
        (http.Request req) async => http.Response(
          jsonEncode(<String, String>{
            "correlation_id": "c-1",
            "record_key": "r-1",
          }),
          200,
        ),
      ),
    );
    final GovernedWriteResult r = await client.governedWrite(
      requestedBy: "drew",
      purpose: "demo",
      targetKey: "k",
      payload: <String, dynamic>{"a": 1},
    );
    expect(r.correlationId, "c-1");
    expect(r.recordKey, "r-1");
  });

  test("the fixture demo build carries no backend address", () {
    // Tests compile without the dart-define, exactly like the pure demo:
    // no address, no live claims anywhere.
    expect(forgeApiConfigured, isFalse);
  });

  test("a 3xx response with JSON is a denial, never a success", () async {
    final ForgeApiClient client = clientWith(
      MockClient(
        (http.Request req) async => http.Response(
          jsonEncode(<String, String>{
            "correlation_id": "c",
            "record_key": "r",
          }),
          302,
        ),
      ),
    );
    await expectLater(
      client.governedWrite(
        requestedBy: "drew",
        purpose: "demo",
        targetKey: "k",
        payload: <String, dynamic>{},
      ),
      throwsA(isA<ForgeDenial>()),
    );
  });

  test(
    "a 200 with missing fields is a controlled denial, not a crash",
    () async {
      final ForgeApiClient client = clientWith(
        MockClient(
          (http.Request req) async =>
              http.Response(jsonEncode(<String, int>{"unexpected": 1}), 200),
        ),
      );
      await expectLater(
        client.evaluate(targetKey: "k", payload: <String, dynamic>{}),
        throwsA(
          isA<ForgeDenial>().having(
            (ForgeDenial d) => d.code,
            "code",
            "RESPONSE_NOT_UNDERSTOOD",
          ),
        ),
      );
    },
  );
}
