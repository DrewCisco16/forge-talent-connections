// FIXTURE DATA - NOT PRODUCTION TRUTH
//
// Every name, count, percentage, identifier and fit score in this file is a
// demo fixture. None of it describes a real person, credential, organisation or
// verification outcome. Nothing here may be migrated into a production claim.
//
// These values exist so the UI can be demonstrated end to end without a
// backend. When the real backend is attached, this file is deleted.
import "../models/models.dart";

/// Which set of fixtures to serve.
///
/// The same screens render against all three, which is how the honest failure
/// paths are demonstrated rather than described.
enum DemoScenario {
  /// The happy path: checks passed.
  verified("Verified", "Checks passed"),

  /// Waiting on outcomes. Nothing is presented as success while pending.
  pending("Pending", "Waiting on checks"),

  /// Checks failed or work is locked. Denials render explicitly.
  denied("Denied", "Checks failed, export blocked");

  const DemoScenario(this.label, this.blurb);

  final String label;
  final String blurb;
}

/// Bundled avatar artwork.
const List<AvatarOption> kAvatars = <AvatarOption>[
  AvatarOption(id: "hero_01", asset: "assets/heroes/hero_01.png"),
  AvatarOption(id: "hero_02", asset: "assets/heroes/hero_02.png"),
  AvatarOption(id: "hero_03", asset: "assets/heroes/hero_03.png"),
  AvatarOption(id: "hero_04", asset: "assets/heroes/hero_04.png"),
  AvatarOption(id: "hero_05", asset: "assets/heroes/hero_05.png"),
  AvatarOption(id: "hero_06", asset: "assets/heroes/hero_06.png"),
  AvatarOption(id: "hero_07", asset: "assets/heroes/hero_07.png"),
  AvatarOption(id: "hero_08", asset: "assets/heroes/hero_08.png"),
  AvatarOption(id: "hero_09", asset: "assets/heroes/hero_09.png"),
  AvatarOption(id: "hero_10", asset: "assets/heroes/hero_10.png"),
  AvatarOption(id: "hero_11", asset: "assets/heroes/hero_11.png"),
  AvatarOption(id: "hero_12", asset: "assets/heroes/hero_12.png"),
  AvatarOption(id: "hero_13", asset: "assets/heroes/hero_13.png"),
  AvatarOption(id: "hero_14", asset: "assets/heroes/hero_14.png"),
  AvatarOption(id: "hero_15", asset: "assets/heroes/hero_15.png"),
  AvatarOption(id: "hero_16", asset: "assets/heroes/hero_16.png"),
];

/// The signed-in demo persona's avatar.
///
/// Drew Cisco is the stand-in for the product owner, so the avatar is male.
/// Named here rather than indexed into [kAvatars] so it cannot drift when the
/// grid order changes, and so every surface showing "you" shows the same face.
const String kDrewAvatar = "assets/heroes/hero_10.png";

/// Index of [kDrewAvatar] within [kAvatars], for the selection grid.
const int kDrewAvatarIndex = 9;

/// The flame mark, ready for a dark background.
const String kFlameMark = "assets/brand/forge_flame.png";

/// The FORGE wordmark artwork, in the brand's own lettering.
const String kWordmark = "assets/brand/forge_wordmark.png";

/// Branches of service. Flag colours are authentic and exempt from theming.
const List<ServiceBranch> kBranches = <ServiceBranch>[
  ServiceBranch(
      id: "usmc",
      name: "United States Marine Corps",
      shortName: "USMC",
      motto: "Semper Fidelis"),
  ServiceBranch(
      id: "usa", name: "United States Army", shortName: "USA", motto: "This We'll Defend"),
  ServiceBranch(
      id: "usn", name: "United States Navy", shortName: "USN", motto: "Semper Fortis"),
  ServiceBranch(
      id: "usaf",
      name: "United States Air Force",
      shortName: "USAF",
      motto: "Aim High"),
  ServiceBranch(
      id: "uscg",
      name: "United States Coast Guard",
      shortName: "USCG",
      motto: "Semper Paratus"),
  ServiceBranch(
      id: "ussf",
      name: "United States Space Force",
      shortName: "USSF",
      motto: "Semper Supra"),
];

/// Opportunities shown on discovery. Fixture organisations.
const List<Opportunity> kOpportunities = <Opportunity>[
  Opportunity(
    id: "employment-law-presentation",
    title: "Employment Law Presentation",
    organization: "FIU Business School",
    organizationKind: "University",
    organizationStatus: VerificationStatus.verified,
    description:
        "Build the slide deck and speaker materials for a graduate employment law seminar. Clear visuals, sourced citations, and a case-study walkthrough.",
    tags: <TechTag>[
      TechTag("Research", TechTagTone.violet),
      TechTag("Slides", TechTagTone.gold),
      TechTag("Legal", TechTagTone.cyan),
    ],
    pills: <String>["Project", "Remote", "6 weeks"],
    deliverables: <String>[
      "A 40-slide presentation with speaker notes",
      "A sourced case-study appendix",
      "One rehearsal session with the teaching team",
    ],
  ),
  Opportunity(
    id: "analytics-capstone",
    title: "Business Analytics Capstone Dashboard",
    organization: "FIU Business School",
    organizationKind: "University",
    organizationStatus: VerificationStatus.verified,
    description:
        "Stand up the live dashboard for the analytics capstone cohort. Data engineering plus a clean reviewer view for faculty.",
    tags: <TechTag>[
      TechTag("Flutter", TechTagTone.gold),
      TechTag("FastAPI", TechTagTone.green),
      TechTag("Analytics", TechTagTone.cyan),
    ],
    pills: <String>["Project", "Hybrid", "One semester"],
    deliverables: <String>[
      "A working dashboard against the cohort dataset",
      "Faculty reviewer documentation",
      "Handover session with the program office",
    ],
  ),
  Opportunity(
    id: "entrepreneurship-pitch",
    title: "Entrepreneurship Pitch Competition Portal",
    organization: "FIU Business School",
    organizationKind: "University",
    organizationStatus: VerificationStatus.pending,
    description:
        "Build the submission and judging portal for the spring pitch competition. Team registration, deliverable uploads, judge scoring.",
    tags: <TechTag>[
      TechTag("UX", TechTagTone.violet),
      TechTag("Figma", TechTagTone.gold),
      TechTag("Web", TechTagTone.cyan),
    ],
    pills: <String>["Project", "Remote", "8 weeks"],
    deliverables: <String>[
      "Registration and submission flows",
      "Judge scoring view with an audit trail",
    ],
  ),
];

/// Stories on the social feed.
const List<Story> kStories = <Story>[
  Story(id: "self", name: "You", avatar: "assets/heroes/hero_10.png", isSelf: true),
  Story(id: "maya", name: "Maya", avatar: "assets/heroes/hero_04.png"),
  Story(id: "jordan", name: "Jordan", avatar: "assets/heroes/hero_12.png"),
  Story(id: "ana", name: "Ana", avatar: "assets/heroes/hero_06.png"),
  Story(id: "kai", name: "Kai", avatar: "assets/heroes/hero_14.png"),
];

/// Feed entries.
const List<FeedPost> kFeed = <FeedPost>[
  FeedPost(
    id: "post-0",
    authorName: "Maya Chen",
    authorAvatar: "assets/heroes/hero_04.png",
    authorStatus: VerificationStatus.verified,
    event: "sealed a project milestone",
    body:
        "Discovery on the Employment Law Presentation is sealed. Congratulations to the whole team — every file passed its check.",
    vouchCount: 12,
  ),
  FeedPost(
    id: "post-1",
    authorName: "Maya Chen",
    authorAvatar: "assets/heroes/hero_04.png",
    authorStatus: VerificationStatus.verified,
    event: "shipped a verified deliverable",
    body: "Closed out the capstone dashboard milestone two days early.",
    vouchCount: 9,
  ),
  FeedPost(
    id: "post-2",
    authorName: "Jordan Reyes",
    authorAvatar: "assets/heroes/hero_12.png",
    authorStatus: VerificationStatus.verified,
    event: "earned a credential",
    body: "Cloud Practitioner cleared its check this morning.",
    vouchCount: 4,
  ),
  FeedPost(
    id: "post-3",
    authorName: "Ana Duarte",
    authorAvatar: "assets/heroes/hero_06.png",
    authorStatus: VerificationStatus.pending,
    event: "submitted work for checking",
    body: "Accessibility pass is in review. Will post the findings once it clears.",
    vouchCount: 2,
  ),
];

/// Vouches on the trust wallet.
const List<Vouch> kVouches = <Vouch>[
  Vouch(
    id: "v1",
    fromName: "Maya Chen",
    fromAvatar: "assets/heroes/hero_04.png",
    scope: "Both",
    text: "Drew ran incident response for us under real pressure. Calm, exact, honest about what he did not know.",
    signedOn: "Aug 2026",
    basis: "Worked together on Employment Law Presentation",
    basisStatus: VerificationStatus.verified,
  ),
  Vouch(
    id: "v2",
    fromName: "Jordan Reyes",
    fromAvatar: "assets/heroes/hero_12.png",
    scope: "Skills",
    text: "The Splunk work held up. I checked it myself against the raw feed.",
    signedOn: "Jul 2026",
    basis: "Reviewed verified deliverables directly",
    basisStatus: VerificationStatus.verified,
  ),
  Vouch(
    id: "v3",
    fromName: "Ana Duarte",
    fromAvatar: "assets/heroes/hero_06.png",
    scope: "Character",
    text: "Said no to a shortcut that would have cost us later. That is the whole recommendation.",
    signedOn: "Jun 2026",
    basis: "Knows Drew outside a shared project",
    basisStatus: VerificationStatus.unverified,
  ),
];

/// Concept pathway data. Fit figures are placeholders, not model output.
const List<PathwayMatch> kPathways = <PathwayMatch>[
  PathwayMatch(role: "Network Engineer", fitPercent: 94),
  PathwayMatch(role: "Cloud Support Specialist", fitPercent: 88),
  PathwayMatch(role: "IT Operations Analyst", fitPercent: 82),
];
