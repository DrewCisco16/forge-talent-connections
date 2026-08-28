import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../features/core/b1_dashboard.dart";
import "../features/core/b2_find_opportunities.dart";
import "../features/core/b3_resume_builder.dart";
import "../features/core/b4_credentials.dart";
import "../features/core/b5_trust_wallet.dart";
import "../features/core/b6_ai_match.dart";
import "../features/core/b7_opportunity_detail.dart";
import "../features/onboarding/a1_splash.dart";
import "../features/onboarding/a2_create_profile.dart";
import "../features/onboarding/a3_choose_avatar.dart";
import "../features/onboarding/a4_veteran_verification.dart";
import "../features/onboarding/a5_elevator_pitch.dart";
import "../features/social/c1_feed.dart";
import "../features/social/c2_video_pitch.dart";
import "../features/social/c3_vouch_flow.dart";
import "../features/social/c4_chat.dart";
import "../features/social/c5_notifications.dart";
import "../features/trust/d1_export_certificate.dart";
import "../features/trust/d2_project_space.dart";
import "../features/trust/d3_sign_in.dart";
import "../features/trust/d4_profile_settings.dart";
import "../features/trust/d5_veteran_pathways.dart";
import "app_shell.dart";
import "widget_gallery.dart";

/// Every screen in the application.
///
/// Onboarding, the story player and the design gallery sit outside the tab
/// shell; everything else is reachable from the bottom navigation.
GoRouter buildRouter() {
  return GoRouter(
    initialLocation: "/",
    routes: <RouteBase>[
      // Flow A: onboarding and identity.
      GoRoute(path: "/", name: "splash", builder: (_, __) => const A1Splash()),
      GoRoute(
        path: "/create-profile",
        name: "create-profile",
        builder: (_, __) => const A2CreateProfile(),
      ),
      GoRoute(
        path: "/choose-avatar",
        name: "choose-avatar",
        builder: (_, __) => const A3ChooseAvatar(),
      ),
      GoRoute(
        path: "/veteran-verification",
        name: "veteran-verification",
        builder: (_, __) => const A4VeteranVerification(),
      ),
      GoRoute(
        path: "/elevator-pitch",
        name: "elevator-pitch",
        builder: (_, __) => const A5ElevatorPitch(),
      ),

      // Full-bleed and standalone screens.
      GoRoute(
        path: "/sign-in",
        name: "sign-in",
        builder: (_, __) => const D3SignIn(),
      ),
      GoRoute(
        path: "/video-pitch",
        name: "video-pitch",
        builder: (_, __) => const C2VideoPitch(),
      ),
      GoRoute(
        path: "/gallery",
        name: "gallery",
        builder: (_, __) => const WidgetGallery(),
      ),

      // The tabbed application shell.
      ShellRoute(
        builder: (BuildContext context, GoRouterState state, Widget child) =>
            AppShell(location: state.uri.path, child: child),
        routes: <RouteBase>[
          GoRoute(
            path: "/dashboard",
            name: "dashboard",
            builder: (_, __) => const B1Dashboard(),
          ),
          GoRoute(
            path: "/opportunities",
            name: "opportunities",
            builder: (_, __) => const B2FindOpportunities(),
          ),
          GoRoute(
            path: "/opportunity/:id",
            name: "opportunity",
            builder: (BuildContext context, GoRouterState state) =>
                B7OpportunityDetail(
              opportunityId: state.pathParameters["id"]!,
            ),
          ),
          GoRoute(
            path: "/match/:id",
            name: "match",
            builder: (BuildContext context, GoRouterState state) => B6AiMatch(
              opportunityId: state.pathParameters["id"]!,
            ),
          ),
          GoRoute(
            path: "/resume-builder",
            name: "resume-builder",
            builder: (_, __) => const B3ResumeBuilder(),
          ),
          GoRoute(
            path: "/credentials",
            name: "credentials",
            builder: (_, __) => const B4Credentials(),
          ),
          GoRoute(
            path: "/trust-wallet",
            name: "trust-wallet",
            builder: (_, __) => const B5TrustWallet(),
          ),
          GoRoute(
            path: "/feed",
            name: "feed",
            builder: (_, __) => const C1Feed(),
          ),
          GoRoute(
            path: "/vouch",
            name: "vouch",
            builder: (_, __) => const C3VouchFlow(),
          ),
          GoRoute(
            path: "/chat",
            name: "chat",
            builder: (_, __) => const C4Chat(),
          ),
          GoRoute(
            path: "/notifications",
            name: "notifications",
            builder: (_, __) => const C5Notifications(),
          ),
          GoRoute(
            path: "/export",
            name: "export",
            builder: (_, __) => const D1ExportCertificate(),
          ),
          GoRoute(
            path: "/project-space",
            name: "project-space",
            builder: (_, __) => const D2ProjectSpace(),
          ),
          GoRoute(
            path: "/profile",
            name: "profile",
            builder: (_, __) => const D4ProfileSettings(),
          ),
          GoRoute(
            path: "/pathways",
            name: "pathways",
            builder: (_, __) => const D5VeteranPathways(),
          ),
        ],
      ),
    ],
  );
}
