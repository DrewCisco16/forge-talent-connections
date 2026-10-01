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

    return _decode(response);
  }

  /// Extracts a typed field from a response body; a missing or wrongly
  /// typed field is a controlled denial, never a raw runtime error.
  T _field<T>(Map<String, dynamic> body, String key) {
    final dynamic v = body[key];
    if (v is T) return v;
    throw ForgeDenial(
      code: "RESPONSE_NOT_UNDERSTOOD",
      message:
          "We received a response we could not confirm. "
          "Nothing was changed.",
      nextStep: "Please try again.",
      retryable: false,
      httpStatus: 200,
    );
  }

  /// A read from the backend, with the same strict success window and
  /// denial mapping as a write. Reads may be retried by the caller; this
  /// method itself never retries.
  Future<Map<String, dynamic>> get(String path) async {
    http.Response response;
    try {
      response = await _http
          .get(Uri.parse("$baseUrl$path"), headers: _headers)
          .timeout(const Duration(seconds: 30));
    } catch (_) {
      throw ForgeDenial.transport();
    }
    return _decode(response);
  }

  /// Shared response handling: JSON object or RESPONSE_NOT_UNDERSTOOD; only
  /// 2xx without a "denied" status counts as success.
  Map<String, dynamic> _decode(http.Response response) {
    Map<String, dynamic> decoded;
    try {
      // Bytes, decoded as UTF-8 regardless of the declared charset: a server
      // that omits "charset=utf-8" would otherwise have its text read as
      // Latin-1 and every non-ASCII character in a record would be garbled.
      final dynamic parsed = jsonDecode(utf8.decode(response.bodyBytes));
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
    if (response.statusCode < 200 ||
        response.statusCode >= 300 ||
        decoded["status"] == "denied") {
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
      final dynamic body = jsonDecode(utf8.decode(r.bodyBytes));
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
    return _field<Map<String, dynamic>>(body, "token");
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
      correlationId: _field<String>(body, "correlation_id"),
      recordKey: _field<String>(body, "record_key"),
    );
  }

  // ---------------------------------------------------------- record changes
  //
  // Each of these asks the backend to change a record under its rules. The
  // backend may refuse (a ForgeDenial, rendered as given) or record the
  // change as pending a named human's decision. Nothing here is optimistic:
  // the screen shows the backend's answer, never an assumed success.

  /// Puts the signed-in person's name behind [toUser]. The backend decides
  /// whether the basis is a shared verified project; the returned
  /// `basis_status` says so, and the vouch counts toward the gate only then.
  Future<Map<String, dynamic>> giveVouch({
    required String toUser,
    required String scope,
    required String text,
    String? basis,
  }) => _post("/api/v1/vouches", <String, dynamic>{
    "to_user": toUser,
    "scope": scope,
    "text": text,
    "basis": basis,
  });

  /// Applies to a listing. Always pending; a named reviewer decides.
  Future<Map<String, dynamic>> applyToOpportunity(String opportunityId) =>
      _post(
        "/api/v1/opportunities/${Uri.encodeComponent(opportunityId)}/apply",
        const <String, dynamic>{},
      );

  /// Submits work for checking. Always pending until a reviewer decides.
  Future<Map<String, dynamic>> submitDeliverable(String name) => _post(
    "/api/v1/project-space/deliverables",
    <String, dynamic>{"name": name},
  );

  Future<Map<String, dynamic>> _put(
    String path,
    Map<String, dynamic> body,
  ) async {
    http.Response response;
    try {
      response = await _http
          .put(
            Uri.parse("$baseUrl$path"),
            headers: _headers,
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 30));
    } catch (_) {
      throw ForgeDenial.transport();
    }
    return _decode(response);
  }

  // ---------------------------------------------------------- every other feature

  /// Updates the person's own profile facts. Completion is counted by the
  /// backend from what is on file.
  Future<Map<String, dynamic>> updateProfile({
    String? displayName,
    String? about,
    List<String>? skills,
    String? avatarAsset,
  }) => _put("/api/v1/profile", <String, dynamic>{
    if (displayName != null) "display_name": displayName,
    if (about != null) "about": about,
    if (skills != null) "skills": skills,
    if (avatarAsset != null) "avatar_asset": avatarAsset,
  });

  /// Submits a service record for sealing. Pending until a reviewer decides.
  Future<Map<String, dynamic>> submitVeteranVerification({
    required String branchId,
    required String documentName,
  }) => _post("/api/v1/veteran-verification", <String, dynamic>{
    "branch_id": branchId,
    "document_name": documentName,
  });

  /// Submits a credential for checking. Pending until a reviewer decides.
  Future<Map<String, dynamic>> addCredential({
    required String title,
    String? identifier,
  }) => _post("/api/v1/credentials", <String, dynamic>{
    "title": title,
    "identifier": identifier,
  });

  Future<Map<String, dynamic>> updateElevatorPitch({
    String? videoAsset,
    String? transcript,
    bool? captionsOn,
    bool? isAiPresented,
  }) => _put("/api/v1/elevator-pitch", <String, dynamic>{
    if (videoAsset != null) "video_asset": videoAsset,
    if (transcript != null) "transcript": transcript,
    if (captionsOn != null) "captions_on": captionsOn,
    if (isAiPresented != null) "is_ai_presented": isAiPresented,
  });

  Future<Map<String, dynamic>> recordConsent(String version) =>
      _post("/api/v1/legal/consent", <String, dynamic>{"version": version});

  Future<Map<String, dynamic>> sendMessage({
    required String text,
    String? attachmentName,
  }) => _post("/api/v1/chat/messages", <String, dynamic>{
    "text": text,
    "attachment_name": attachmentName,
  });

  /// Marks notifications read; null marks all of them.
  Future<Map<String, dynamic>> markNotificationsRead([List<String>? ids]) =>
      _post("/api/v1/notifications/read", <String, dynamic>{"ids": ids});

  /// The feed's vouch tap: an endorsement, once per post, never a gate vouch.
  Future<Map<String, dynamic>> endorsePost(String postId) =>
      _post("/api/v1/feed/endorse", <String, dynamic>{"post_id": postId});

  Future<Map<String, dynamic>> postTalentStory({
    required String headline,
    required String caption,
    List<String> tags = const <String>[],
    String? videoAsset,
  }) => _post("/api/v1/talent-stories", <String, dynamic>{
    "headline": headline,
    "caption": caption,
    "tags": tags,
    "video_asset": videoAsset,
  });

  /// Asks for a file to leave. Cleared only for verified work; otherwise
  /// locked with the reason.
  Future<Map<String, dynamic>> requestExport(String deliverableId) => _post(
    "/api/v1/export/requests",
    <String, dynamic>{"deliverable_id": deliverableId},
  );

  /// Anyone may check a seal. The answer is verified or unknown.
  Future<Map<String, dynamic>> sealCheck(String fingerprint) => _post(
    "/api/v1/seal-check",
    <String, dynamic>{"fingerprint": fingerprint},
  );

  Future<Map<String, dynamic>> pitchStudioConsent(bool consent) => _post(
    "/api/v1/pitch-studio/consent",
    <String, dynamic>{"consent": consent},
  );

  Future<Map<String, dynamic>> regeneratePortfolioDraft() =>
      _post("/api/v1/portfolio-draft/regenerate", const <String, dynamic>{});

  Future<Map<String, dynamic>> regenerateTalentSignature() =>
      _post("/api/v1/talent-signature/regenerate", const <String, dynamic>{});

  Future<Map<String, dynamic>> redeemReferral(String code) =>
      _post("/api/v1/rewards/referrals", <String, dynamic>{"code": code});

  Future<Map<String, dynamic>> requestDecisionReview(String decisionId) =>
      _post(
        "/api/v1/decisions/${Uri.encodeComponent(decisionId)}/review-request",
        const <String, dynamic>{},
      );

  Future<Map<String, dynamic>> recomputeMatch(String opportunityId) => _post(
    "/api/v1/opportunities/${Uri.encodeComponent(opportunityId)}/match/recompute",
    const <String, dynamic>{},
  );

  /// Asks the assistant a question. Grounded in the verified record; the
  /// answer is appended to the transcript and changes nothing else.
  Future<Map<String, dynamic>> askAssistant(String question) =>
      _post("/api/v1/assistant/ask", <String, dynamic>{"question": question});

  void close() => _http.close();
}
