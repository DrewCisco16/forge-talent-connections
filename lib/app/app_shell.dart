import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../widgets/bottom_nav.dart";

/// The tabbed shell: five destinations with the bottom navigation bar.
class AppShell extends StatelessWidget {
  const AppShell({required this.child, required this.location, super.key});

  final Widget child;
  final String location;

  static const Map<ForgeTab, String> _routes = <ForgeTab, String>{
    ForgeTab.home: "/dashboard",
    ForgeTab.discover: "/opportunities",
    ForgeTab.create: "/feed",
    ForgeTab.projects: "/project-space",
    ForgeTab.me: "/profile",
  };

  ForgeTab get _current {
    for (final MapEntry<ForgeTab, String> e in _routes.entries) {
      if (location.startsWith(e.value)) return e.key;
    }
    return ForgeTab.home;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: child,
      bottomNavigationBar: BottomNav(
        current: _current,
        onSelected: (ForgeTab tab) => context.go(_routes[tab]!),
      ),
    );
  }
}
