import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "app/app.dart";

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // The designs are portrait-only at a 390x844 baseline. Landscape would render
  // a layout that was never specified, so it is not offered.
  SystemChrome.setPreferredOrientations(<DeviceOrientation>[
    DeviceOrientation.portraitUp,
  ]);
  runApp(const ProviderScope(child: ForgeApp()));
}
