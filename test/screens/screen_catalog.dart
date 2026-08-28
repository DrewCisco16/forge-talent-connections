import "package:flutter/material.dart";
import "package:forge_talent_connections/features/core/b1_dashboard.dart";
import "package:forge_talent_connections/features/core/b2_find_opportunities.dart";
import "package:forge_talent_connections/features/core/b3_resume_builder.dart";
import "package:forge_talent_connections/features/core/b4_credentials.dart";
import "package:forge_talent_connections/features/core/b5_trust_wallet.dart";
import "package:forge_talent_connections/features/core/b6_ai_match.dart";
import "package:forge_talent_connections/features/core/b7_opportunity_detail.dart";
import "package:forge_talent_connections/features/onboarding/a1_splash.dart";
import "package:forge_talent_connections/features/onboarding/a2_create_profile.dart";
import "package:forge_talent_connections/features/onboarding/a3_choose_avatar.dart";
import "package:forge_talent_connections/features/onboarding/a4_veteran_verification.dart";
import "package:forge_talent_connections/features/onboarding/a5_elevator_pitch.dart";
import "package:forge_talent_connections/features/social/c1_feed.dart";
import "package:forge_talent_connections/features/social/c2_video_pitch.dart";
import "package:forge_talent_connections/features/social/c3_vouch_flow.dart";
import "package:forge_talent_connections/features/social/c4_chat.dart";
import "package:forge_talent_connections/features/social/c5_notifications.dart";
import "package:forge_talent_connections/features/trust/d1_export_certificate.dart";
import "package:forge_talent_connections/features/trust/d2_project_space.dart";
import "package:forge_talent_connections/features/trust/d3_sign_in.dart";
import "package:forge_talent_connections/features/trust/d4_profile_settings.dart";
import "package:forge_talent_connections/features/trust/d5_veteran_pathways.dart";
import "package:forge_talent_connections/features/trust/trust_technology.dart";

/// Every screen in the application, keyed by its specification label.
///
/// One list, used by both the render suite and the responsive suite, so a new
/// screen cannot be added to one and forgotten in the other.
final Map<String, Widget> screenCatalog = <String, Widget>{
  "A1 Splash": const A1Splash(),
  "A2 Create Profile": const A2CreateProfile(),
  "A3 Choose Avatar": const A3ChooseAvatar(),
  "A4 Veteran Verification": const A4VeteranVerification(),
  "A5 Elevator Pitch": const A5ElevatorPitch(),
  "B1 Dashboard": const B1Dashboard(),
  "B2 Find Opportunities": const B2FindOpportunities(),
  "B3 Resume Builder": const B3ResumeBuilder(),
  "B4 Credentials": const B4Credentials(),
  "B5 Trust Wallet": const B5TrustWallet(),
  "B6 AI Match": const B6AiMatch(opportunityId: "atlas-telemetry"),
  "B7 Opportunity Detail": const B7OpportunityDetail(
    opportunityId: "atlas-telemetry",
  ),
  "C1 Feed": const C1Feed(),
  "C2 Video Pitch": const C2VideoPitch(),
  "C3 Vouch Flow": const C3VouchFlow(),
  "C4 Chat": const C4Chat(),
  "C5 Notifications": const C5Notifications(),
  "D1 Export Certificate": const D1ExportCertificate(),
  "D2 Project Space": const D2ProjectSpace(),
  "D3 Sign In": const D3SignIn(),
  "D4 Profile Settings": const D4ProfileSettings(),
  "D5 Veteran Pathways": const D5VeteranPathways(),
  "Trust Technology": const TrustTechnology(),
};
