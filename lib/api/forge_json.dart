import "../models/models.dart";
import "forge_api_client.dart";

/// The wire format between the product backend and this UI.
///
/// One codec per model, in both directions. Reading is strict: a missing or
/// wrongly typed field is a controlled denial (RESPONSE_NOT_UNDERSTOOD), never
/// a raw runtime error, so a backend that drifts from this contract can only
/// produce the app's honest "could not confirm" state. Writing exists so the
/// fixtures can be exported as the backend's seed and so round trips can be
/// tested. Field names are snake_case on the wire.
class ForgeJson {
  ForgeJson._();

  // ------------------------------------------------------------ helpers

  static ForgeDenial _bad(String what) => ForgeDenial(
    code: "RESPONSE_NOT_UNDERSTOOD",
    message:
        "We received a response we could not confirm. Nothing was changed.",
    nextStep: "Please try again.",
    retryable: false,
    httpStatus: 200,
  );

  static Map<String, dynamic> _map(Object? v, String what) {
    if (v is Map<String, dynamic>) return v;
    if (v is Map) return Map<String, dynamic>.from(v);
    throw _bad(what);
  }

  static T _req<T>(Map<String, dynamic> m, String k) {
    final Object? v = m[k];
    if (v is T) return v;
    throw _bad(k);
  }

  static T? _opt<T>(Map<String, dynamic> m, String k) {
    final Object? v = m[k];
    if (v == null) return null;
    if (v is T) return v as T;
    throw _bad(k);
  }

  static List<String> _strings(Map<String, dynamic> m, String k) {
    final Object? v = m[k];
    if (v == null) return const <String>[];
    if (v is List && v.every((Object? e) => e is String)) {
      return List<String>.unmodifiable(v.cast<String>());
    }
    throw _bad(k);
  }

  static List<T> _list<T>(
    Map<String, dynamic> m,
    String k,
    T Function(Map<String, dynamic>) decode,
  ) {
    final Object? v = m[k];
    if (v == null) return const [];
    if (v is! List) throw _bad(k);
    return List<T>.unmodifiable(v.map((Object? e) => decode(_map(e, k))));
  }

  static VerificationStatus _status(Object? v, String what) {
    if (v is String) {
      for (final VerificationStatus s in VerificationStatus.values) {
        if (s.name == v) return s;
      }
    }
    throw _bad(what);
  }

  static VerificationStatus? _statusOpt(Object? v, String what) =>
      v == null ? null : _status(v, what);

  /// Unwraps `{"items": [...]}`, the shape every list endpoint returns.
  static List<T> items<T>(
    Map<String, dynamic> body,
    T Function(Map<String, dynamic>) decode,
  ) => _list<T>(body, "items", decode);

  static Map<String, dynamic> wrapItems(List<Map<String, dynamic>> items) =>
      <String, dynamic>{"items": items};

  // ------------------------------------------------------------ profile

  static UserProfile profile(Map<String, dynamic> m) => UserProfile(
    displayName: _req<String>(m, "display_name"),
    skills: _strings(m, "skills"),
    about: _req<String>(m, "about"),
    avatarAsset: _opt<String>(m, "avatar_asset"),
    completionPercent: _req<int>(m, "completion_percent"),
    serviceRecord: _status(m["service_record"], "service_record"),
  );

  static Map<String, dynamic> profileJson(UserProfile p) => <String, dynamic>{
    "display_name": p.displayName,
    "skills": p.skills,
    "about": p.about,
    "avatar_asset": p.avatarAsset,
    "completion_percent": p.completionPercent,
    "service_record": p.serviceRecord.name,
  };

  static AvatarOption avatar(Map<String, dynamic> m) =>
      AvatarOption(id: _req<String>(m, "id"), asset: _req<String>(m, "asset"));

  static Map<String, dynamic> avatarJson(AvatarOption a) => <String, dynamic>{
    "id": a.id,
    "asset": a.asset,
  };

  static ServiceBranch branch(Map<String, dynamic> m) => ServiceBranch(
    id: _req<String>(m, "id"),
    name: _req<String>(m, "name"),
    shortName: _req<String>(m, "short_name"),
    motto: _req<String>(m, "motto"),
  );

  static Map<String, dynamic> branchJson(ServiceBranch b) => <String, dynamic>{
    "id": b.id,
    "name": b.name,
    "short_name": b.shortName,
    "motto": b.motto,
  };

  static ElevatorPitch elevatorPitch(Map<String, dynamic> m) => ElevatorPitch(
    durationSeconds: _req<int>(m, "duration_seconds"),
    positionSeconds: _req<int>(m, "position_seconds"),
    captionsOn: _req<bool>(m, "captions_on"),
    isAiPresented: _req<bool>(m, "is_ai_presented"),
    videoAsset: _opt<String>(m, "video_asset"),
    transcript: _opt<String>(m, "transcript"),
  );

  static Map<String, dynamic> elevatorPitchJson(ElevatorPitch p) =>
      <String, dynamic>{
        "duration_seconds": p.durationSeconds,
        "position_seconds": p.positionSeconds,
        "captions_on": p.captionsOn,
        "is_ai_presented": p.isAiPresented,
        "video_asset": p.videoAsset,
        "transcript": p.transcript,
      };

  // ------------------------------------------------------------ opportunity

  static TechTag techTag(Map<String, dynamic> m) {
    final String tone = _req<String>(m, "tone");
    for (final TechTagTone t in TechTagTone.values) {
      if (t.name == tone) return TechTag(_req<String>(m, "label"), t);
    }
    throw _bad("tone");
  }

  static Map<String, dynamic> techTagJson(TechTag t) => <String, dynamic>{
    "label": t.label,
    "tone": t.tone.name,
  };

  static Opportunity opportunity(Map<String, dynamic> m) => Opportunity(
    id: _req<String>(m, "id"),
    title: _req<String>(m, "title"),
    organization: _req<String>(m, "organization"),
    organizationKind: _req<String>(m, "organization_kind"),
    organizationStatus: _status(
      m["organization_status"],
      "organization_status",
    ),
    description: _req<String>(m, "description"),
    tags: _list<TechTag>(m, "tags", techTag),
    pills: _strings(m, "pills"),
    deliverables: _strings(m, "deliverables"),
    engagement: _opt<String>(m, "engagement"),
    vouchLevel: _opt<String>(m, "vouch_level"),
    evidence: _strings(m, "evidence"),
    seatsOpen: _opt<int>(m, "seats_open"),
    seatsTotal: _opt<int>(m, "seats_total"),
    reviewerConfirmed: _opt<bool>(m, "reviewer_confirmed"),
    scopeOnFile: _opt<bool>(m, "scope_on_file"),
    startWindow: _opt<String>(m, "start_window"),
    expiresOn: _opt<String>(m, "expires_on"),
    qualified: _opt<bool>(m, "qualified"),
  );

  static Map<String, dynamic> opportunityJson(Opportunity o) =>
      <String, dynamic>{
        "id": o.id,
        "title": o.title,
        "organization": o.organization,
        "organization_kind": o.organizationKind,
        "organization_status": o.organizationStatus.name,
        "description": o.description,
        "tags": o.tags.map(techTagJson).toList(),
        "pills": o.pills,
        "deliverables": o.deliverables,
        "engagement": o.engagement,
        "vouch_level": o.vouchLevel,
        "evidence": o.evidence,
        "seats_open": o.seatsOpen,
        "seats_total": o.seatsTotal,
        "reviewer_confirmed": o.reviewerConfirmed,
        "scope_on_file": o.scopeOnFile,
        "start_window": o.startWindow,
        "expires_on": o.expiresOn,
        "qualified": o.qualified,
      };

  static MatchFactor matchFactor(Map<String, dynamic> m) {
    final String kind = _req<String>(m, "kind");
    for (final MatchFactorKind k in MatchFactorKind.values) {
      if (k.name == kind) return MatchFactor(_req<String>(m, "text"), k);
    }
    throw _bad("kind");
  }

  static Map<String, dynamic> matchFactorJson(MatchFactor f) =>
      <String, dynamic>{"text": f.text, "kind": f.kind.name};

  static MatchSuggestion matchSuggestion(Map<String, dynamic> m) =>
      MatchSuggestion(
        opportunityId: _req<String>(m, "opportunity_id"),
        opportunityTitle: _req<String>(m, "opportunity_title"),
        score: _req<int>(m, "score"),
        headline: _req<String>(m, "headline"),
        factors: _list<MatchFactor>(m, "factors", matchFactor),
        reviewState: _status(m["review_state"], "review_state"),
      );

  static Map<String, dynamic> matchSuggestionJson(MatchSuggestion s) =>
      <String, dynamic>{
        "opportunity_id": s.opportunityId,
        "opportunity_title": s.opportunityTitle,
        "score": s.score,
        "headline": s.headline,
        "factors": s.factors.map(matchFactorJson).toList(),
        "review_state": s.reviewState.name,
      };

  // ------------------------------------------------------------ trust

  static Credential credential(Map<String, dynamic> m) => Credential(
    id: _req<String>(m, "id"),
    title: _req<String>(m, "title"),
    status: _status(m["status"], "status"),
    identifier: _opt<String>(m, "identifier"),
    validThrough: _opt<String>(m, "valid_through"),
    sealedOn: _opt<String>(m, "sealed_on"),
    failureReason: _opt<String>(m, "failure_reason"),
  );

  static Map<String, dynamic> credentialJson(Credential c) => <String, dynamic>{
    "id": c.id,
    "title": c.title,
    "status": c.status.name,
    "identifier": c.identifier,
    "valid_through": c.validThrough,
    "sealed_on": c.sealedOn,
    "failure_reason": c.failureReason,
  };

  static Deliverable deliverable(Map<String, dynamic> m) => Deliverable(
    id: _req<String>(m, "id"),
    name: _req<String>(m, "name"),
    status: _status(m["status"], "status"),
    submittedOn: _opt<String>(m, "submitted_on"),
    failureReason: _opt<String>(m, "failure_reason"),
  );

  static Map<String, dynamic> deliverableJson(Deliverable d) =>
      <String, dynamic>{
        "id": d.id,
        "name": d.name,
        "status": d.status.name,
        "submitted_on": d.submittedOn,
        "failure_reason": d.failureReason,
      };

  static Vouch vouch(Map<String, dynamic> m) => Vouch(
    id: _req<String>(m, "id"),
    fromName: _req<String>(m, "from_name"),
    fromAvatar: _req<String>(m, "from_avatar"),
    scope: _req<String>(m, "scope"),
    text: _req<String>(m, "text"),
    signedOn: _req<String>(m, "signed_on"),
    basis: _opt<String>(m, "basis"),
    basisStatus:
        _statusOpt(m["basis_status"], "basis_status") ??
        VerificationStatus.unverified,
  );

  static Map<String, dynamic> vouchJson(Vouch v) => <String, dynamic>{
    "id": v.id,
    "from_name": v.fromName,
    "from_avatar": v.fromAvatar,
    "scope": v.scope,
    "text": v.text,
    "signed_on": v.signedOn,
    "basis": v.basis,
    "basis_status": v.basisStatus.name,
  };

  static TrustWalletSummary walletSummary(Map<String, dynamic> m) =>
      TrustWalletSummary(
        deliverables: _req<int>(m, "deliverables"),
        credentials: _req<int>(m, "credentials"),
        vouches: _req<int>(m, "vouches"),
      );

  static Map<String, dynamic> walletSummaryJson(TrustWalletSummary w) =>
      <String, dynamic>{
        "deliverables": w.deliverables,
        "credentials": w.credentials,
        "vouches": w.vouches,
      };

  static Milestone milestone(Map<String, dynamic> m) => Milestone(
    name: _req<String>(m, "name"),
    status: _status(m["status"], "status"),
  );

  static Map<String, dynamic> milestoneJson(Milestone m) => <String, dynamic>{
    "name": m.name,
    "status": m.status.name,
  };

  static ProjectSpace projectSpace(Map<String, dynamic> m) => ProjectSpace(
    projectName: _req<String>(m, "project_name"),
    organization: _req<String>(m, "organization"),
    milestones: _list<Milestone>(m, "milestones", milestone),
    deliverables: _list<Deliverable>(m, "deliverables", deliverable),
    activity: _strings(m, "activity"),
    teamNorms: _strings(m, "team_norms"),
    checkInPrompt: _opt<String>(m, "check_in_prompt"),
  );

  static Map<String, dynamic> projectSpaceJson(ProjectSpace p) =>
      <String, dynamic>{
        "project_name": p.projectName,
        "organization": p.organization,
        "milestones": p.milestones.map(milestoneJson).toList(),
        "deliverables": p.deliverables.map(deliverableJson).toList(),
        "activity": p.activity,
        "team_norms": p.teamNorms,
        "check_in_prompt": p.checkInPrompt,
      };

  static ExportItem exportItem(Map<String, dynamic> m) => ExportItem(
    id: _req<String>(m, "id"),
    filename: _req<String>(m, "filename"),
    status: _status(m["status"], "status"),
    reason: _opt<String>(m, "reason"),
  );

  static Map<String, dynamic> exportItemJson(ExportItem e) => <String, dynamic>{
    "id": e.id,
    "filename": e.filename,
    "status": e.status.name,
    "reason": e.reason,
  };

  static IntegrityCertificate certificate(Map<String, dynamic> m) =>
      IntegrityCertificate(
        filename: _req<String>(m, "filename"),
        status: _status(m["status"], "status"),
        checkedOn: _req<String>(m, "checked_on"),
        fingerprint: _req<String>(m, "fingerprint"),
        deliveredAsCreated: _req<bool>(m, "delivered_as_created"),
      );

  static Map<String, dynamic> certificateJson(IntegrityCertificate c) =>
      <String, dynamic>{
        "filename": c.filename,
        "status": c.status.name,
        "checked_on": c.checkedOn,
        "fingerprint": c.fingerprint,
        "delivered_as_created": c.deliveredAsCreated,
      };

  static RoadMatch road(Map<String, dynamic> m) => RoadMatch(
    role: _req<String>(m, "role"),
    fitPercent: _req<int>(m, "fit_percent"),
  );

  static Map<String, dynamic> roadJson(RoadMatch r) => <String, dynamic>{
    "role": r.role,
    "fit_percent": r.fitPercent,
  };

  // ------------------------------------------------------------ social

  static Story story(Map<String, dynamic> m) => Story(
    id: _req<String>(m, "id"),
    name: _req<String>(m, "name"),
    avatar: _req<String>(m, "avatar"),
    isSelf: _opt<bool>(m, "is_self") ?? false,
  );

  static Map<String, dynamic> storyJson(Story s) => <String, dynamic>{
    "id": s.id,
    "name": s.name,
    "avatar": s.avatar,
    "is_self": s.isSelf,
  };

  static TalentStory talentStory(Map<String, dynamic> m) => TalentStory(
    id: _req<String>(m, "id"),
    authorName: _req<String>(m, "author_name"),
    authorAvatar: _req<String>(m, "author_avatar"),
    authorStatus: _status(m["author_status"], "author_status"),
    headline: _req<String>(m, "headline"),
    caption: _req<String>(m, "caption"),
    vouchCount: _req<int>(m, "vouch_count"),
    tags: _strings(m, "tags"),
  );

  static Map<String, dynamic> talentStoryJson(TalentStory s) =>
      <String, dynamic>{
        "id": s.id,
        "author_name": s.authorName,
        "author_avatar": s.authorAvatar,
        "author_status": s.authorStatus.name,
        "headline": s.headline,
        "caption": s.caption,
        "vouch_count": s.vouchCount,
        "tags": s.tags,
      };

  static FeedPost feedPost(Map<String, dynamic> m) => FeedPost(
    id: _req<String>(m, "id"),
    authorName: _req<String>(m, "author_name"),
    authorAvatar: _req<String>(m, "author_avatar"),
    authorStatus: _status(m["author_status"], "author_status"),
    event: _req<String>(m, "event"),
    body: _req<String>(m, "body"),
    vouchCount: _req<int>(m, "vouch_count"),
  );

  static Map<String, dynamic> feedPostJson(FeedPost p) => <String, dynamic>{
    "id": p.id,
    "author_name": p.authorName,
    "author_avatar": p.authorAvatar,
    "author_status": p.authorStatus.name,
    "event": p.event,
    "body": p.body,
    "vouch_count": p.vouchCount,
  };

  static ChatMessage chatMessage(Map<String, dynamic> m) => ChatMessage(
    id: _req<String>(m, "id"),
    text: _req<String>(m, "text"),
    fromMe: _req<bool>(m, "from_me"),
    sentAt: _req<String>(m, "sent_at"),
    attachmentName: _opt<String>(m, "attachment_name"),
    attachmentStatus: _statusOpt(m["attachment_status"], "attachment_status"),
  );

  static Map<String, dynamic> chatMessageJson(ChatMessage c) =>
      <String, dynamic>{
        "id": c.id,
        "text": c.text,
        "from_me": c.fromMe,
        "sent_at": c.sentAt,
        "attachment_name": c.attachmentName,
        "attachment_status": c.attachmentStatus?.name,
      };

  static ChatThread chatThread(Map<String, dynamic> m) => ChatThread(
    withName: _req<String>(m, "with_name"),
    presence: _req<String>(m, "presence"),
    messages: _list<ChatMessage>(m, "messages", chatMessage),
  );

  static Map<String, dynamic> chatThreadJson(ChatThread t) => <String, dynamic>{
    "with_name": t.withName,
    "presence": t.presence,
    "messages": t.messages.map(chatMessageJson).toList(),
  };

  static AppNotification notification(Map<String, dynamic> m) {
    final String kind = _req<String>(m, "kind");
    NotificationKind? found;
    for (final NotificationKind k in NotificationKind.values) {
      if (k.name == kind) found = k;
    }
    if (found == null) throw _bad("kind");
    return AppNotification(
      id: _req<String>(m, "id"),
      kind: found,
      title: _req<String>(m, "title"),
      body: _req<String>(m, "body"),
      when: _req<String>(m, "when"),
      unread: _req<bool>(m, "unread"),
      isToday: _req<bool>(m, "is_today"),
    );
  }

  static Map<String, dynamic> notificationJson(AppNotification n) =>
      <String, dynamic>{
        "id": n.id,
        "kind": n.kind.name,
        "title": n.title,
        "body": n.body,
        "when": n.when,
        "unread": n.unread,
        "is_today": n.isToday,
      };

  // ------------------------------------------------------------ growth

  static MembershipStatus membership(Map<String, dynamic> m) =>
      MembershipStatus(
        vouchesReceived: _req<int>(m, "vouches_received"),
        vouchesRequired: _req<int>(m, "vouches_required"),
        earnedLaneLabel: _req<String>(m, "earned_lane_label"),
        earnedLaneStatus: _status(
          m["earned_lane_status"],
          "earned_lane_status",
        ),
        gateOpen: _req<bool>(m, "gate_open"),
      );

  static Map<String, dynamic> membershipJson(MembershipStatus s) =>
      <String, dynamic>{
        "vouches_received": s.vouchesReceived,
        "vouches_required": s.vouchesRequired,
        "earned_lane_label": s.earnedLaneLabel,
        "earned_lane_status": s.earnedLaneStatus.name,
        "gate_open": s.gateOpen,
      };

  static DraftLine draftLine(Map<String, dynamic> m) => DraftLine(
    text: _req<String>(m, "text"),
    sourceLabel: _req<String>(m, "source_label"),
  );

  static DeclinedClaim declinedClaim(Map<String, dynamic> m) => DeclinedClaim(
    claim: _req<String>(m, "claim"),
    reason: _req<String>(m, "reason"),
  );

  static AssistantDraft portfolioDraft(Map<String, dynamic> m) =>
      AssistantDraft(
        lines: _list<DraftLine>(m, "lines", draftLine),
        declined: _list<DeclinedClaim>(m, "declined", declinedClaim),
      );

  static Map<String, dynamic> portfolioDraftJson(AssistantDraft d) =>
      <String, dynamic>{
        "lines": d.lines
            .map(
              (DraftLine l) => <String, dynamic>{
                "text": l.text,
                "source_label": l.sourceLabel,
              },
            )
            .toList(),
        "declined": d.declined
            .map(
              (DeclinedClaim c) => <String, dynamic>{
                "claim": c.claim,
                "reason": c.reason,
              },
            )
            .toList(),
      };

  static VerifiedSkill verifiedSkill(Map<String, dynamic> m) => VerifiedSkill(
    name: _req<String>(m, "name"),
    source: _req<String>(m, "source"),
    status: _status(m["status"], "status"),
  );

  static Map<String, dynamic> verifiedSkillJson(VerifiedSkill s) =>
      <String, dynamic>{
        "name": s.name,
        "source": s.source,
        "status": s.status.name,
      };

  static IntegrityStreak streak(Map<String, dynamic> m) => IntegrityStreak(
    count: _req<int>(m, "count"),
    label: _req<String>(m, "label"),
    note: _req<String>(m, "note"),
    active: _req<bool>(m, "active"),
  );

  static Map<String, dynamic> streakJson(IntegrityStreak s) =>
      <String, dynamic>{
        "count": s.count,
        "label": s.label,
        "note": s.note,
        "active": s.active,
      };

  static GivenVouch givenVouch(Map<String, dynamic> m) => GivenVouch(
    toName: _req<String>(m, "to_name"),
    toAvatar: _req<String>(m, "to_avatar"),
    basis: _req<String>(m, "basis"),
    signedOn: _req<String>(m, "signed_on"),
  );

  static Map<String, dynamic> givenVouchJson(GivenVouch v) => <String, dynamic>{
    "to_name": v.toName,
    "to_avatar": v.toAvatar,
    "basis": v.basis,
    "signed_on": v.signedOn,
  };

  static SystemDecision decision(Map<String, dynamic> m) => SystemDecision(
    id: _req<String>(m, "id"),
    what: _req<String>(m, "what"),
    why: _req<String>(m, "why"),
    when: _req<String>(m, "when"),
    canRequestReview: _req<bool>(m, "can_request_review"),
  );

  static Map<String, dynamic> decisionJson(SystemDecision d) =>
      <String, dynamic>{
        "id": d.id,
        "what": d.what,
        "why": d.why,
        "when": d.when,
        "can_request_review": d.canRequestReview,
      };

  static PitchStudio pitchStudio(Map<String, dynamic> m) => PitchStudio(
    consentOnFile: _req<bool>(m, "consent_on_file"),
    likenessConfidencePercent: _req<int>(m, "likeness_confidence_percent"),
    requiredConfidencePercent: _req<int>(m, "required_confidence_percent"),
    status: _status(m["status"], "status"),
    note: _req<String>(m, "note"),
  );

  static Map<String, dynamic> pitchStudioJson(PitchStudio p) =>
      <String, dynamic>{
        "consent_on_file": p.consentOnFile,
        "likeness_confidence_percent": p.likenessConfidencePercent,
        "required_confidence_percent": p.requiredConfidencePercent,
        "status": p.status.name,
        "note": p.note,
      };

  static RewardEvent rewardEvent(Map<String, dynamic> m) => RewardEvent(
    label: _req<String>(m, "label"),
    points: _req<int>(m, "points"),
    status: _status(m["status"], "status"),
    when: _req<String>(m, "when"),
  );

  static Map<String, dynamic> rewardEventJson(RewardEvent e) =>
      <String, dynamic>{
        "label": e.label,
        "points": e.points,
        "status": e.status.name,
        "when": e.when,
      };

  static RewardPrize rewardPrize(Map<String, dynamic> m) => RewardPrize(
    title: _req<String>(m, "title"),
    detail: _req<String>(m, "detail"),
    valueLabel: _req<String>(m, "value_label"),
  );

  static Map<String, dynamic> rewardPrizeJson(RewardPrize p) =>
      <String, dynamic>{
        "title": p.title,
        "detail": p.detail,
        "value_label": p.valueLabel,
      };

  static LeaderEntry leader(Map<String, dynamic> m) => LeaderEntry(
    name: _req<String>(m, "name"),
    points: _req<int>(m, "points"),
    avatar: _req<String>(m, "avatar"),
  );

  static Map<String, dynamic> leaderJson(LeaderEntry l) => <String, dynamic>{
    "name": l.name,
    "points": l.points,
    "avatar": l.avatar,
  };

  static RewardsProgram rewards(Map<String, dynamic> m) => RewardsProgram(
    quarterLabel: _req<String>(m, "quarter_label"),
    quarterEnds: _req<String>(m, "quarter_ends"),
    pointsVerified: _req<int>(m, "points_verified"),
    pointsPending: _req<int>(m, "points_pending"),
    standingNote: _req<String>(m, "standing_note"),
    membersEarning: _req<int>(m, "members_earning"),
    referralCode: _req<String>(m, "referral_code"),
    referralsJoined: _req<int>(m, "referrals_joined"),
    referralsPending: _req<int>(m, "referrals_pending"),
    topThree: _list<LeaderEntry>(m, "top_three", leader),
    events: _list<RewardEvent>(m, "events", rewardEvent),
    quarterlyPrizes: _list<RewardPrize>(m, "quarterly_prizes", rewardPrize),
    yearlyPrize: rewardPrize(_map(m["yearly_prize"], "yearly_prize")),
    status: _status(m["status"], "status"),
    note: _req<String>(m, "note"),
  );

  static Map<String, dynamic> rewardsJson(RewardsProgram r) =>
      <String, dynamic>{
        "quarter_label": r.quarterLabel,
        "quarter_ends": r.quarterEnds,
        "points_verified": r.pointsVerified,
        "points_pending": r.pointsPending,
        "standing_note": r.standingNote,
        "members_earning": r.membersEarning,
        "referral_code": r.referralCode,
        "referrals_joined": r.referralsJoined,
        "referrals_pending": r.referralsPending,
        "top_three": r.topThree.map(leaderJson).toList(),
        "events": r.events.map(rewardEventJson).toList(),
        "quarterly_prizes": r.quarterlyPrizes.map(rewardPrizeJson).toList(),
        "yearly_prize": rewardPrizeJson(r.yearlyPrize),
        "status": r.status.name,
        "note": r.note,
      };

  static AssistantExchange assistantExchange(Map<String, dynamic> m) =>
      AssistantExchange(
        question: _req<String>(m, "question"),
        answer: _req<String>(m, "answer"),
        premium: _opt<bool>(m, "premium") ?? false,
        sampleResults: _strings(m, "sample_results"),
      );

  static Map<String, dynamic> assistantExchangeJson(AssistantExchange e) =>
      <String, dynamic>{
        "question": e.question,
        "answer": e.answer,
        "premium": e.premium,
        "sample_results": e.sampleResults,
      };

  static SignatureStrength signatureStrength(Map<String, dynamic> m) =>
      SignatureStrength(
        name: _req<String>(m, "name"),
        evidence: _req<String>(m, "evidence"),
        status: _status(m["status"], "status"),
      );

  static TalentSignature talentSignature(Map<String, dynamic> m) =>
      TalentSignature(
        summary: _req<String>(m, "summary"),
        strengths: _list<SignatureStrength>(m, "strengths", signatureStrength),
        refusals: _strings(m, "refusals"),
      );

  static Map<String, dynamic> talentSignatureJson(TalentSignature s) =>
      <String, dynamic>{
        "summary": s.summary,
        "strengths": s.strengths
            .map(
              (SignatureStrength x) => <String, dynamic>{
                "name": x.name,
                "evidence": x.evidence,
                "status": x.status.name,
              },
            )
            .toList(),
        "refusals": s.refusals,
      };
}
