import "package:go_router/go_router.dart";

import "widget_gallery.dart";

/// Application routes.
///
/// Only the design system gallery exists at this milestone. Product screens are
/// added flow by flow in the milestones that follow.
GoRouter buildRouter() {
  return GoRouter(
    initialLocation: "/gallery",
    routes: <RouteBase>[
      GoRoute(
        path: "/gallery",
        name: "gallery",
        builder: (_, __) => const WidgetGallery(),
      ),
    ],
  );
}
