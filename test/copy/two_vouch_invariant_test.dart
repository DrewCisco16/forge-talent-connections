import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/mock_repository.dart";
import "package:forge_talent_connections/models/models.dart";

/// The exact two-human access invariant, pinned at the fixture seam.
///
/// The backend owns enforcement; this walled UI must never RENDER a state
/// that violates the rule. These tests fail the build if any fixture set
/// ever serves an open gate without exactly two distinct accountable human
/// vouches, a self-vouch, a blank voucher, duplicate vouchers, or supply
/// that claims to be qualified without the facts behind it.
void main() {
  for (final DemoScenario scenario in DemoScenario.values) {
    group("scenario $scenario", () {
      final MockForgeRepository repo = MockForgeRepository(scenario);

      test("the gate opens only on exactly two vouches", () async {
        final MembershipStatus m = await repo.loadMembership();
        expect(
          m.vouchesRequired,
          2,
          reason: "membership always requires exactly two",
        );
        expect(
          m.gateOpen,
          m.vouchesReceived == 2,
          reason:
              "an open gate must mean exactly two accepted vouches, "
              "and exactly two must mean open",
        );
        expect(
          m.vouchesReceived,
          lessThanOrEqualTo(2),
          reason: "more than two accepted access vouches is invalid",
        );
      });

      test(
        "served vouches are distinct, named humans, never the member",
        () async {
          final List<Vouch> vouches = await repo.loadVouches();
          final Set<String> names = <String>{};
          for (final Vouch v in vouches) {
            expect(
              v.fromName.trim(),
              isNotEmpty,
              reason: "a blank voucher identity is invalid",
            );
            expect(
              v.fromName,
              isNot("Drew Cisco"),
              reason: "self-vouching is invalid",
            );
            expect(
              names.add(v.fromName),
              isTrue,
              reason: "duplicate voucher ${v.fromName} is invalid",
            );
          }
        },
      );

      test("given vouches are distinct and never self-directed", () async {
        final List<GivenVouch> given = await repo.loadGivenVouches();
        final Set<String> names = <String>{};
        for (final GivenVouch g in given) {
          expect(g.toName.trim(), isNotEmpty);
          expect(g.toName, isNot("Drew Cisco"));
          expect(names.add(g.toName), isTrue);
        }
      });

      test(
        "every decision about the person carries a human appeal path",
        () async {
          final List<SystemDecision> decisions = await repo.loadDecisions();
          for (final SystemDecision d in decisions) {
            expect(
              d.canRequestReview,
              isTrue,
              reason: "${d.id} lacks a human review path",
            );
          }
        },
      );

      test("qualified supply is backed by its facts", () async {
        final List<Opportunity> all = await repo.loadOpportunities();
        for (final Opportunity o in all) {
          if (o.qualified == true) {
            expect(
              o.organizationStatus,
              VerificationStatus.verified,
              reason: "${o.id}: qualified requires a verified sponsor",
            );
            expect(o.seatsOpen, isNotNull);
            expect(
              o.seatsOpen! > 0,
              isTrue,
              reason: "${o.id}: qualified requires open seats",
            );
            expect(
              o.reviewerConfirmed,
              isTrue,
              reason: "${o.id}: qualified requires reviewer capacity",
            );
            expect(
              o.scopeOnFile,
              isTrue,
              reason: "${o.id}: qualified requires a written scope",
            );
            expect(
              o.seatsOpen! <= (o.seatsTotal ?? 0),
              isTrue,
              reason:
                  "${o.id}: open seats cannot exceed total seats, "
                  "so invitations cannot exceed capacity",
            );
          }
        }
      });

      test(
        "no fixture copy lets anything substitute for a human vouch",
        () async {
          final MembershipStatus m = await repo.loadMembership();
          expect(
            m.earnedLaneLabel.toLowerCase(),
            isNot(contains("counts as")),
            reason: "evidence informs reviewers; it never counts as a vouch",
          );
        },
      );
    });
  }
}
