# iPhone Demo: Loading FORGE Talent Connections on a Test iPhone

This guide covers getting the Flutter application onto an iPhone 16 Pro Max
for demonstration. It is written for a first-time reader; every path is
listed with what it needs, what it costs, and how long the install lasts.

The iOS project in `ios/` is ready to build: bundle id
`com.forgelink.forgeTalentConnections`, display name "FORGE Talent
Connections", portrait only, deployment target iOS 15.0, phoenix medallion
app icons and launch image, and the elevator pitch video bundled from
`assets/media/forge_ad.mp4`.

## The one fact that decides the path

Apple only lets iOS applications be compiled and signed on macOS with Xcode.
A Windows laptop, a Linux machine, or this cloud session cannot produce an
iPhone build. Every path below either uses a Mac or rents one.

| Path | Needs | Cost | Install lasts | Time to first run |
| --- | --- | --- | --- | --- |
| A. Home screen web app | The iPhone only | Free | Until removed | 1 minute |
| B. Mac with Xcode, free Apple ID | Any Mac, USB cable | Free | 7 days, then re-run | 30 to 60 minutes first time |
| C. Mac with Xcode, Apple Developer Program | Any Mac, USB cable | 99 USD per year | 1 year | 30 to 60 minutes first time |
| D. TestFlight via a cloud Mac | Apple Developer Program, Codemagic or GitHub Actions | 99 USD per year plus build minutes | 90 days per build | 1 to 2 hours setup |

Path A works today with nothing to install. Path C is the right long-term
setup for a demo phone. Path D is the way to get native builds without
owning a Mac.

## Path A: Home screen web app (available now)

The demo is already a standalone web application. On the iPhone:

1. Open Safari and go to https://www.forgetalentconnections.com/demo/
2. Tap the Share button (the square with the arrow).
3. Tap "Add to Home Screen", then "Add".

The medallion icon appears on the home screen and the demo opens full
screen without Safari's address bar, in portrait, with the navy loading
screen. This is what to use for a demonstration this week.

Limits: it is the web build, so the video plays through Safari's player
and there is no offline use. If an old icon shows, remove the shortcut and
add it again; iPhones cache the first icon they saw.

## Path B: Mac with Xcode and a free Apple ID

Any Mac from the last several years works, including a borrowed one.

1. Install Xcode from the Mac App Store (large download; allow an hour).
   Open it once and accept the license.
2. Install Flutter 3.47.2. The simplest route is FVM:
   ```bash
   brew install fvm
   git clone https://github.com/DrewCisco16/forge-talent-connections.git
   cd forge-talent-connections
   fvm install && fvm use 3.47.2
   fvm flutter doctor
   ```
   `flutter doctor` must show Xcode with a green check.
3. Connect the iPhone by USB. On the phone, tap "Trust This Computer".
4. On the phone, turn on Developer Mode: Settings, Privacy & Security,
   Developer Mode, then restart the phone when asked. (iOS 16 and later
   require this for any app installed outside the App Store.)
5. Open the project in Xcode and pick a team:
   ```bash
   fvm flutter pub get
   open ios/Runner.xcworkspace
   ```
   In Xcode: click "Runner" in the left column, then the "Runner" target,
   then "Signing & Capabilities". Tick "Automatically manage signing" and
   choose your Apple ID under "Team" (add it through Xcode, Settings,
   Accounts if it is not listed). With a free Apple ID, Xcode may ask you
   to change the bundle identifier to something unique; append your
   initials, for example `com.forgelink.forgeTalentConnections.af`.
6. Build and install:
   ```bash
   fvm flutter devices
   fvm flutter run --release -d <the iPhone's id from the list>
   ```
7. The first launch is blocked until the phone trusts the developer:
   Settings, General, VPN & Device Management, tap your Apple ID, tap
   Trust.

With a free Apple ID the app stops opening after 7 days. Plug the phone in
and run step 6 again to renew it. Up to three apps can be installed this
way at a time.

## Path C: Mac with Xcode and the Apple Developer Program

Same as Path B, with two differences:

- Enroll at https://developer.apple.com/programs/ (99 USD per year, takes
  a day or two to approve). Add that Apple ID as the team in step 5.
- The installed app lasts a year, and TestFlight becomes available for
  handing the demo to other testers without a cable.

For a demo phone that gets shown repeatedly, this is the path to choose.

## Path D: TestFlight from a cloud Mac (no Mac to own)

This rents a Mac for each build and delivers the app through TestFlight, so
the iPhone installs it from the TestFlight app with no cable.

Needs, in order:

1. Apple Developer Program membership (Path C, first bullet).
2. In App Store Connect, create the app record with bundle id
   `com.forgelink.forgeTalentConnections`.
3. An App Store Connect API key (Users and Access, Integrations, App Store
   Connect API, generate a key with the App Manager role). Download the
   `.p8` file once; note the Key ID and Issuer ID.
4. A build service with macOS runners. Two that work with this repository
   as-is:
   - Codemagic (https://codemagic.io): connect the GitHub repository,
     choose the Flutter workflow, enable iOS code signing with the API key
     from step 3, set "Publish to TestFlight". Codemagic creates the
     certificates and profiles itself.
   - GitHub Actions on a macOS runner: the workflow file
     `docs/ios/build-ios.yml` in this repository is a ready template.
     Copy it to `.github/workflows/build-ios.yml`, add the four secrets it
     names (the API key file as base64, Key ID, Issuer ID, and the team
     id), and push. The workflow archives, signs, and uploads to
     TestFlight.
5. On the iPhone, install TestFlight from the App Store, accept the
   invitation sent to your Apple ID, and install the build.

Each TestFlight build lasts 90 days. Never commit the API key, the `.p8`
file, or any certificate to the repository; they belong in the service's
secret store.

## What the phone will show

- The phoenix medallion icon on the home screen, and the medallion on the
  launch screen while iOS starts the app.
- The splash, Mission, sign-in, and every header with the shining
  medallion, exactly as on the web demo.
- The elevator pitch playing from the bundled file. The bundled encode is
  the cleaned original supplied in August. That source is small, and no
  build can add detail that the source does not carry. To ship a sharper
  pitch, place the full-resolution master in the shared Google Drive; the
  encode step in this repository's history is repeatable and the file
  drops in at `assets/media/forge_ad.mp4`.

## Checks before handing the phone over

- Open the app in airplane mode once: the demo runs entirely on fixtures
  and must not stall on any network call.
- Play the elevator pitch to the end with the phone's silent switch off.
- Rotate the phone: the app stays portrait by design.
- Open Settings, Accessibility, Display & Text Size, and raise the text
  size two steps: every screen must remain readable with no clipped text.
