import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "app/app.dart";

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Orientation is decided by ForgeDeviceFrame, which can tell a phone from a
  // tablet. Setting it here as well would fight it.
  runApp(const ProviderScope(child: ForgeApp()));
}
