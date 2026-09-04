import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/core/talent_signature.dart";
import "package:forge_talent_connections/features/onboarding/mission.dart";
import "package:forge_talent_connections/features/social/talent_stories.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// The founder's two within-the-year feature previews hold their honest
/// frames: Talent Stories labels its samples and invents no footage, the
/// Talent Signature carries evidence for every strength and prints its own
/// refusals, and the Mission screen states the road ahead with the AR
/// timing the founder set.
void main() {
  Future<void> pumpScreen(WidgetTester tester, Widget screen) async {
    tester.view.physicalSize = const Size(440, 4600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: buildForgeTheme(),
          home: MediaQuery(
            data: const MediaQueryData(
              size: Size(440, 4600),
              disableAnimations: true,
            ),
            child: screen,
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets("Talent Stories is a labelled sample browser", (
    WidgetTester tester,
  ) async {
    await pumpScreen(tester, const TalentStories());
    expect(find.text("Talent Stories"), findsOneWidget);
    // The first sample author renders with a caption, and the counter says
    // where the swipe stands.
    expect(find.text("Drew"), findsOneWidget);
    expect(find.text("1 of 4"), findsOneWidget);
    expect(find.text("Vouch"), findsWidgets);
    // Honesty: samples are labelled, footage is never invented, and the
    // production timing is the founder's own.
    expect(
      find.textContaining("no footage is invented for sample people"),
      findsOneWidget,
    );
    expect(find.textContaining("Within the year"), findsOneWidget);
    expect(find.textContaining("same verification standard"), findsOneWidget);
  });

  testWidgets("the Talent Signature carries evidence and refusals", (
    WidgetTester tester,
  ) async {
    await pumpScreen(tester, const TalentSignatureScreen());
    expect(find.text("Talent Signature"), findsOneWidget);
    expect(
      find.text("Your strengths, drawn only from your verified record"),
      findsOneWidget,
    );
    // Every strength names its evidence; pending evidence reads pending.
    expect(find.text("Incident response"), findsOneWidget);
    expect(find.text("Sealed service record"), findsOneWidget);
    expect(find.text("Credential still checking"), findsOneWidget);
    // The refusals are printed as product copy.
    // SectionLabel renders capitalised.
    expect(find.text("WHAT THIS NEVER DOES"), findsOneWidget);
    expect(find.text("No personality scores, ever."), findsOneWidget);
    expect(
      find.text("No predictions about your future, ever."),
      findsOneWidget,
    );
    // Production home, consent, and the legal gate, named out loud.
    expect(find.textContaining("Google Cloud Vertex AI"), findsOneWidget);
    expect(find.textContaining("after legal review"), findsWidgets);
    expect(find.textContaining("labelled sample"), findsOneWidget);
  });

  testWidgets("the Mission screen states the founder's road ahead", (
    WidgetTester tester,
  ) async {
    await pumpScreen(tester, const MissionScreen());
    // SectionLabel renders capitalised.
    expect(find.text("THE ROAD AHEAD"), findsOneWidget);
    expect(
      find.textContaining(
        "Within the year: Talent Stories, the Talent Signature",
      ),
      findsOneWidget,
    );
    // AR carries the founder's timing and the feasibility condition.
    expect(
      find.textContaining("first year after official release"),
      findsOneWidget,
    );
    expect(
      find.textContaining("as the content and the technology prove ready"),
      findsOneWidget,
    );
  });
}
