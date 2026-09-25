import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/models/verification_status.dart";
import "package:forge_talent_connections/widgets/status_chip.dart";

import "../support/harness.dart";

void main() {
  group("StatusChip", () {
    testWidgets("renders the exact label for every permitted state", (
      WidgetTester tester,
    ) async {
      const Map<VerificationStatus, String> expected =
          <VerificationStatus, String>{
            VerificationStatus.verified: "VERIFIED",
            VerificationStatus.pending: "PENDING",
            VerificationStatus.unverified: "UNVERIFIED",
            VerificationStatus.failed: "FAILED",
            VerificationStatus.locked: "LOCKED",
          };

      for (final MapEntry<VerificationStatus, String> e in expected.entries) {
        await pumpHarness(tester, StatusChip(status: e.key));
        expect(
          find.text(e.value),
          findsOneWidget,
          reason: "${e.key} must render as ${e.value}",
        );
      }
    });

    testWidgets("supports exactly five states and no more", (
      WidgetTester tester,
    ) async {
      // A sixth state would need Andrew's approval before it could ship.
      expect(VerificationStatus.values.length, 5);
    });

    testWidgets("never renders a non-verified state as verified", (
      WidgetTester tester,
    ) async {
      for (final VerificationStatus s in VerificationStatus.values) {
        if (s == VerificationStatus.verified) continue;
        await pumpHarness(tester, StatusChip(status: s));
        expect(
          find.text("VERIFIED"),
          findsNothing,
          reason: "$s must not be presented as verified",
        );
      }
    });
  });

  group("VerificationStatus", () {
    test("only verified counts as proven", () {
      for (final VerificationStatus s in VerificationStatus.values) {
        expect(s.isProven, s == VerificationStatus.verified);
      }
    });

    test("failed and locked block release", () {
      expect(VerificationStatus.failed.blocksRelease, isTrue);
      expect(VerificationStatus.locked.blocksRelease, isTrue);
      expect(VerificationStatus.verified.blocksRelease, isFalse);
      expect(VerificationStatus.pending.blocksRelease, isFalse);
      expect(VerificationStatus.unverified.blocksRelease, isFalse);
    });
  });
}
