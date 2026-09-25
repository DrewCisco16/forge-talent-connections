# Building FORGE Talent Connections

Toolchain is pinned in `.fvmrc` to **Flutter 3.47.2** (Dart 3.13.2). Use FVM so
every machine and CI resolve the same SDK:

```bash
fvm install && fvm use 3.47.2
fvm flutter --version   # must print 3.47.2
```

Without FVM, plain `flutter` works provided it is 3.47.2.

## Checks (run before every push)

```bash
flutter analyze          # must print: No issues found!
flutter test             # full suite, including goldens
```

Goldens are asserted, not regenerated, by `flutter test`. Regenerate them
deliberately with `flutter test --update-goldens` only when a visual change is
intended, and review the image diff before committing.

## iOS — requires macOS

This project uses **Swift Package Manager**, which is the default iOS plugin
mechanism from Flutter 3.44 onward. There is no `Podfile` and **`pod install`
is not required**; running it will do nothing useful. Xcode resolves the
generated Swift package automatically on first open.

```bash
flutter pub get
open ios/Runner.xcworkspace
```

In Xcode: Runner target → Signing & Capabilities → select your team → choose the
connected device → Run.

Or from the terminal:

```bash
flutter devices
flutter run --release -d <device-id>
```

One build covers iPhone 16 Pro Max, iPhone 17 Pro Max, and iPad Pro 11.
Deployment target is iOS 15.0; bundle id `com.forgelink.forgeTalentConnections`.

## Web demo

```bash
flutter build web --release --base-href /demo/
rm -rf demo && cp -r build/web demo && rm -rf demo/canvaskit
```

`demo/canvaskit/` is gitignored: this build fetches the renderer from Google's
CDN, so the locally emitted copy is dead weight.

## Backend

The app runs entirely on fixtures. `lib/api/forge_repository.dart` declares the
interfaces; `lib/mock/` implements them. To attach the real service, implement
those interfaces with an HTTP client and change `forgeRepositoryProvider` in
`lib/mock/providers.dart`. No screen changes.

API base URLs arrive via `--dart-define`. No configuration value is committed.
