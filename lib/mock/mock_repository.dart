// FIXTURE DATA - NOT PRODUCTION TRUTH
//
// A stand-in for the backend so the app can be demonstrated without one. It
// serves fixtures and nothing else: it performs no verification, no matching
// and no release decision. It reports outcomes that were written by hand, and
// the scenario selects which set.
//
// When the real backend is attached, this class is replaced by an HTTP client
// implementing the same interfaces and this file is deleted.
import "../api/forge_repository.dart";
import "../models/models.dart";
import "fixtures.dart";

/// Serves fixture data for a chosen [DemoScenario].
class MockForgeRepository implements ForgeRepository {
  const MockForgeRepository(this.scenario);

  final DemoScenario scenario;

  /// A short pause so loading states are visible rather than skipped past.
  static const Duration _latency = Duration(milliseconds: 220);

  Future<T> _serve<T>(T value) =>
      Future<T>.delayed(_latency, () => value);

  /// The state a checked thing lands in for the current scenario.
  VerificationStatus get _outcome => switch (scenario) {
        DemoScenario.verified => VerificationStatus.verified,
        DemoScenario.pending => VerificationStatus.pending,
        DemoScenario.denied => VerificationStatus.failed,
      };

  @override
  Future<UserProfile> loadProfile() => _serve(
        UserProfile(
          displayName: "Drew Cisco",
          skills: const <String>[
            "Network Operations",
            "Splunk",
            "Python",
            "Incident Response",
          ],
          about:
              "Six years running cyber network operations for the Marine Corps.",
          avatarAsset: kDrewAvatar,
          completionPercent: scenario == DemoScenario.verified ? 100 : 72,
          serviceRecord: scenario == DemoScenario.verified
              ? VerificationStatus.verified
              : scenario == DemoScenario.pending
                  ? VerificationStatus.pending
                  : VerificationStatus.failed,
        ),
      );

  @override
  Future<List<AvatarOption>> loadAvatars() => _serve(kAvatars);

  @override
  Future<List<ServiceBranch>> loadBranches() => _serve(kBranches);

  @override
  Future<ElevatorPitch> loadElevatorPitch() => _serve(
        const ElevatorPitch(
          // Nominal values; once the video initializes, its own clock wins.
          durationSeconds: 80,
          positionSeconds: 0,
          captionsOn: true,
          isAiPresented: true,
          // Andrew's AI-made marketing advertisement, bundled with the demo.
          videoAsset: "assets/media/forge_ad.mp4",
          transcript:
              "...six years running cyber network operations...",
        ),
      );

  @override
  Future<List<Opportunity>> loadOpportunities() => _serve(kOpportunities);

  @override
  Future<Opportunity> loadOpportunity(String id) => _serve(
        kOpportunities.firstWhere(
          (Opportunity o) => o.id == id,
          orElse: () => kOpportunities.first,
        ),
      );

  @override
  Future<List<Opportunity>> loadSuggestedOpportunities() =>
      _serve(kOpportunities.take(2).toList());

  @override
  Future<MatchSuggestion> loadMatchSuggestion(String opportunityId) async {
    final Opportunity o = await loadOpportunity(opportunityId);
    return MatchSuggestion(
      opportunityId: o.id,
      opportunityTitle: o.title,
      score: switch (scenario) {
        DemoScenario.verified => 87,
        DemoScenario.pending => 61,
        DemoScenario.denied => 34,
      },
      headline: switch (scenario) {
        DemoScenario.verified => "Strong match",
        DemoScenario.pending => "Possible match",
        DemoScenario.denied => "Weak match",
      },
      factors: const <MatchFactor>[
        MatchFactor(
            "Verified Splunk deliverables on 2 projects", MatchFactorKind.supporting),
        MatchFactor("Cleared credential: Security+ ce", MatchFactorKind.supporting),
        MatchFactor("Timezone overlap 6h", MatchFactorKind.supporting),
        MatchFactor("No prior legal-content projects", MatchFactorKind.against),
      ],
      reviewState: scenario == DemoScenario.verified
          ? VerificationStatus.verified
          : VerificationStatus.pending,
    );
  }

  @override
  Future<List<Credential>> loadCredentials() => _serve(<Credential>[
        Credential(
          id: "c1",
          title: "CompTIA Security+ ce",
          status: scenario == DemoScenario.verified
              ? VerificationStatus.verified
              : VerificationStatus.unverified,
          identifier: "COMP001022334455",
          validThrough: "2028",
        ),
        Credential(
          id: "c2",
          title: "AWS Cloud Practitioner",
          status: _outcome,
          identifier: "AWS-CP-99182",
          failureReason: scenario == DemoScenario.denied
              ? "Issuer record did not match"
              : null,
        ),
        Credential(
          id: "c3",
          title: "USMC Service Record",
          status: scenario == DemoScenario.denied
              ? VerificationStatus.locked
              : scenario == DemoScenario.pending
                  ? VerificationStatus.pending
                  : VerificationStatus.verified,
          sealedOn: scenario == DemoScenario.verified ? "Aug 2026" : null,
          failureReason:
              scenario == DemoScenario.denied ? "Sealed record unavailable" : null,
        ),
        const Credential(
          id: "c4",
          title: "Cisco CCNA",
          status: VerificationStatus.unverified,
          identifier: "CSCO13398201",
        ),
      ]);

  @override
  Future<TrustWalletSummary> loadWalletSummary() => _serve(
        TrustWalletSummary(
          deliverables: scenario == DemoScenario.verified ? 12 : 7,
          credentials: scenario == DemoScenario.verified ? 4 : 1,
          vouches: 9,
        ),
      );

  @override
  Future<List<Vouch>> loadVouches() => _serve(kVouches);

  @override
  Future<ProjectSpace> loadProjectSpace() => _serve(
        ProjectSpace(
          projectName: "Employment Law Presentation",
          organization: "FIU Business School",
          milestones: <Milestone>[
            const Milestone(name: "Discovery", status: VerificationStatus.verified),
            Milestone(name: "Slide deck draft", status: _outcome),
            const Milestone(
                name: "Rehearsal", status: VerificationStatus.unverified),
          ],
          deliverables: <Deliverable>[
            const Deliverable(
              id: "d1",
              name: "Seminar_Outline_v2.pdf",
              status: VerificationStatus.verified,
              submittedOn: "12 Aug",
            ),
            Deliverable(
              id: "d2",
              name: "Slide_Deck_Draft.pptx",
              status: _outcome,
              submittedOn: "24 Aug",
              failureReason: scenario == DemoScenario.denied
                  ? "File does not match what was created"
                  : null,
            ),
            const Deliverable(
              id: "d3",
              name: "Case_Study_Appendix.pdf",
              status: VerificationStatus.pending,
              submittedOn: "26 Aug",
            ),
          ],
          activity: const <String>[
            "Maya Chen approved the outline",
            "You submitted Slide_Deck_Draft.pptx",
            "Checking started on Case_Study_Appendix.pdf",
          ],
        ),
      );

  @override
  Future<List<Story>> loadStories() => _serve(kStories);

  @override
  Future<List<FeedPost>> loadFeed() => _serve(kFeed);

  @override
  Future<ChatThread> loadThread() => _serve(
        ChatThread(
          withName: "Maya Chen",
          presence: "online · FIU project",
          messages: <ChatMessage>[
            const ChatMessage(
              id: "m1",
              text: "Screens are up. Want to walk them at 3?",
              fromMe: false,
              sentAt: "09:12",
            ),
            const ChatMessage(
              id: "m2",
              text: "Works for me. Sending the file now.",
              fromMe: true,
              sentAt: "09:14",
            ),
            ChatMessage(
              id: "m3",
              text: "",
              fromMe: true,
              sentAt: "09:14",
              attachmentName: "Slide_Deck_Draft.pptx",
              attachmentStatus: _outcome,
            ),
            const ChatMessage(
              id: "m4",
              text: "Got it. Reviewing now.",
              fromMe: false,
              sentAt: "09:20",
            ),
          ],
        ),
      );

  @override
  Future<List<AppNotification>> loadNotifications() => _serve(<AppNotification>[
        AppNotification(
          id: "n1",
          kind: NotificationKind.deliverableVerified,
          title: "Deliverable verified",
          body: "Seminar_Outline_v2.pdf passed its check.",
          when: "09:40",
          unread: true,
          isToday: true,
        ),
        const AppNotification(
          id: "n2",
          kind: NotificationKind.matchFound,
          title: "New match found",
          body: "A suggestion is waiting on human review.",
          when: "08:55",
          unread: true,
          isToday: true,
        ),
        if (scenario == DemoScenario.denied)
          const AppNotification(
            id: "n3",
            kind: NotificationKind.exportBlocked,
            title: "Export blocked",
            body: "1 file failed its check and stays locked.",
            when: "08:30",
            unread: true,
            isToday: true,
          ),
        const AppNotification(
          id: "n4",
          kind: NotificationKind.message,
          title: "Message from Maya",
          body: "Screens are up. Want to walk them at 3?",
          when: "Yesterday",
          unread: false,
          isToday: false,
        ),
        const AppNotification(
          id: "n5",
          kind: NotificationKind.milestoneApproved,
          title: "Milestone approved",
          body: "Discovery was approved by Maya Chen.",
          when: "Yesterday",
          unread: false,
          isToday: false,
        ),
      ]);

  @override
  Future<List<ExportItem>> loadExportQueue() => _serve(<ExportItem>[
        const ExportItem(
          id: "e1",
          filename: "Seminar_Outline_v2.pdf",
          status: VerificationStatus.verified,
        ),
        ExportItem(
          id: "e2",
          filename: "Slide_Deck_Draft.pptx",
          status: switch (scenario) {
            DemoScenario.verified => VerificationStatus.verified,
            DemoScenario.pending => VerificationStatus.pending,
            DemoScenario.denied => VerificationStatus.locked,
          },
          reason: scenario == DemoScenario.denied
              ? "Did not match what was created"
              : null,
        ),
        const ExportItem(
          id: "e3",
          filename: "Case_Study_Appendix.pdf",
          status: VerificationStatus.pending,
        ),
      ]);

  @override
  Future<IntegrityCertificate> loadCertificate() => _serve(
        IntegrityCertificate(
          filename: "Seminar_Outline_v2.pdf",
          status: scenario == DemoScenario.denied
              ? VerificationStatus.failed
              : scenario == DemoScenario.pending
                  ? VerificationStatus.pending
                  : VerificationStatus.verified,
          checkedOn: "27 Aug 2026",
          fingerprint: "ab39...e2f1",
          deliveredAsCreated: scenario != DemoScenario.denied,
        ),
      );

  @override
  Future<List<PathwayMatch>> loadPathways(String occupationCode) =>
      _serve(kPathways);
}
