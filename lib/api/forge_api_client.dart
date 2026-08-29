import "dart:async";
import "dart:convert";

import "package:http/http.dart" as http;

/// Compile-time base URL for the live product backend. Supplied by:
///   flutter build web --dart-define=FORGE_API_BASE_URL=https://api.example.com
///
/// When it is absent the app runs exactly as before: every screen on
/// fixtures, nothing live, nothing pretending to be live.
const String kForgeApiBaseUrl = String.fromEnvironment("FORGE_API_BASE_URL");

/// Whether this build was compiled with a live backend address.
bool get forgeApiConfigured => kForgeApiBaseUrl.isNotEmpty;

/// Thrown when a live client is constructed without a base URL: a
/// misconfigured build fails at startup, never at first tap.
class ForgeConfigError implements Exception {
  ForgeConfigError(this.message);
  final String message;
  @override
  String toString() => "ForgeConfigError: $message";
}

/// A denial from the backend. There is no partial-success state in this API:
/// every non-2xx, timeout, transport error, and unrecognised response shape
/// resolves to one of these, and the UI renders its consumer-safe strings
/// verbatim. An unreachable backend is a denial, never an optimistic local
/// write.
class ForgeDenial implements Exception {
  ForgeDenial({
    required this.code,
    required this.message,
    required this.nextStep,
    required this.retryable,
    required this.httpStatus,
  });

  factory ForgeDenial.fromBody(int status, Map<String, dynamic> body) =>
      ForgeDenial(
        code: (body["code"] ?? "UNKNOWN") as String,
        message:
            (body["message"] ??
                    "We could not complete that action. Nothing was changed.")
                as String,
        nextStep: (body["next_step"] ?? "Please try again.") as String,
        retryable: (body["retryable"] ?? false) as bool,
        httpStatus: status,
      );

  /// The network failed before any response arrived.
  factory ForgeDenial.transport() => ForgeDenial(
    code: "SERVICE_UNAVAILABLE",
    message: "We could not reach the service. Nothing was changed.",
    nextStep: "Check your connection and try again.",
    retryable: true,
    httpStatus: 0,
  );

  final String code;
  final String message;
  final String nextStep;
  final bool retryable;
  final int httpStatus;

  /// True when a human reviewer must act before the flow can continue.
  bool get needsHumanReview => code == "REVIEW_REQUIRED";

  @override
  String toString() => "ForgeDenial($code, $httpStatus): $message";
}

/// Result of the single-call governed write.
class GovernedWriteResult {
  GovernedWriteResult({required this.correlationId, required this.recordKey});
  final String correlationId;
  final String recordKey;
}

/// Client for the FORGE Talent Connections product backend.
///
/// Boundary: this client talks only to the product backend's public edge.
/// It never reaches any internal service directly, and it never inspects or
/// constructs an approval object: the token is carried opaquely. Writes are
/// never retried here; a blind retry could repeat a non-idempotent action.
class ForgeApiClient {
  ForgeApiClient({String? baseUrl, http.Client? httpClient, this.clientSecret})
    : baseUrl = (baseUrl ?? kForgeApiBaseUrl).replaceAll(RegExp(r"/+$"), ""),
      _http = httpClient ?? http.Client() {
    if (this.baseUrl.isEmpty) {
      throw ForgeConfigError(
        "FORGE_API_BASE_URL was not supplied at build time. "
        "Rebuild with --dart-define=FORGE_API_BASE_URL=...",
      );
    }
  }

  final String baseUrl;
  final http.Client _http;

  /// Local development only, where no edge proxy injects it. In any deployed
  /// build this must be null: a secret compiled into a web bundle is not a
  /// secret.
  final String? clientSecret;

  Map<String, String> get _headers => <String, String>{
    "Content-Type": "application/json",
    if (clientSecret != null) "X-Forge-Client-Secret": clientSecret!,
  };

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body,
  ) async {
    http.Response response;
    try {
      response = await _http
          .post(
            Uri.parse("$baseUrl$path"),
            headers: _headers,
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 30));
    } catch (_) {
      throw ForgeDenial.transport();
    }

    Map<String, dynamic> decoded;
    try {
      final dynamic parsed = jsonDecode(response.body);
      if (parsed is! Map<String, dynamic>) {
        throw const FormatException("shape");
      }
      decoded = parsed;
    } catch (_) {
      throw ForgeDenial(
        code: "RESPONSE_NOT_UNDERSTOOD",
        message:
            "We received a response we could not confirm. "
            "Nothing was changed.",
        nextStep: "Please try again.",
        retryable: false,
        httpStatus: response.statusCode,
      );
    }

    if (response.statusCode >= 400 || decoded["status"] == "denied") {
      throw ForgeDenial.fromBody(response.statusCode, decoded);
    }
    return decoded;
  }

  /// Health, for the live-connection banner. Any failure is simply false.
  Future<bool> isHealthy() async {
    try {
      final http.Response r = await _http
          .get(Uri.parse("$baseUrl/health"))
          .timeout(const Duration(seconds: 5));
      if (r.statusCode != 200) return false;
      final dynamic body = jsonDecode(r.body);
      return body is Map<String, dynamic> && body["status"] == "ok";
    } catch (_) {
      return false;
    }
  }

  /// Requests an evaluation and returns the opaque approval object.
  /// Throws [ForgeDenial] with [ForgeDenial.needsHumanReview] on escalation.
  Future<Map<String, dynamic>> evaluate({
    required String targetKey,
    required Map<String, dynamic> payload,
  }) async {
    final Map<String, dynamic> body = await _post(
      "/api/v1/evaluate",
      <String, dynamic>{"target_key": targetKey, "payload": payload},
    );
    return body["token"] as Map<String, dynamic>;
  }

  /// The whole documented write path in one call.
  Future<GovernedWriteResult> governedWrite({
    required String requestedBy,
    required String purpose,
    required String targetKey,
    required Map<String, dynamic> payload,
  }) async {
    final Map<String, dynamic> body = await _post(
      "/api/v1/governed-write",
      <String, dynamic>{
        "requested_by": requestedBy,
        "purpose": purpose,
        "target_key": targetKey,
        "payload": payload,
      },
    );
    return GovernedWriteResult(
      correlationId: body["correlation_id"] as String,
      recordKey: body["record_key"] as String,
    );
  }

  void close() => _http.close();
}
