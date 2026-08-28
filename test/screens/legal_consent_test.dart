import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/onboarding/a2_create_profile.dart";
import "package:forge_talent_connections/features/onboarding/legal_terms.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// Sign-up consent is fail-closed and the terms are honest about what they
/// are: a comprehensive demonstration draft, with counsel review named as
/// the step between this text and a launch.
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

  testWidgets("legal screen carries the full agreement and the honest frame",
      (WidgetTester tester) async {
    await pumpScreen(tester, const LegalTerms());
    // The draft names itself a draft, with counsel review before launch.
    expect(find.textContaining("licensed counsel"), findsWidgets);
    // The sections that make the coverage comprehensive. Section labels
    // render uppercased.
    expect(find.text("REWARDS, REFERRALS, AND PRIZES"), findsOneWidget);
    expect(find.text("YOUR PRIVACY"), findsOneWidget);
    expect(
        find.text("YOUR IDENTITY, LIKENESS, AND CONSENT"), findsOneWidget);
    expect(
      find.text("DISPUTES, GOVERNING LAW, AND WHERE CLAIMS GO"),
      findsOneWidget,
    );
    // The anti-automation prize rule is in the agreement itself.
    expect(find.textContaining("referred to law enforcement"), findsWidgets);
    // The draft is anchored to Florida law: the operating company's home
    // state governs, the game-promotion statute is named, and the breach
    // notice window matches the statute.
    expect(
      find.textContaining("Florida limited liability company"),
      findsOneWidget,
    );
    expect(
      find.textContaining("governed by the laws of the State of Florida"),
      findsOneWidget,
    );
    expect(
      find.textContaining("chapter 849 of the Florida Statutes"),
      findsOneWidget,
    );
    expect(find.textContaining("no more than 30 days"), findsOneWidget);
  });

  testWidgets("sign-up cannot continue until the terms are agreed",
      (WidgetTester tester) async {
    await pumpScreen(tester, const A2CreateProfile());
    // Fail-closed: the gate is visibly shut before consent.
    expect(find.text("Agree to the terms to continue"), findsOneWidget);
    expect(find.text("Agree & Continue"), findsNothing);

    await tester.tap(find.textContaining("I have read and agree"));
    await tester.pump();

    expect(find.text("Agree & Continue"), findsOneWidget);
    expect(find.text("Agree to the terms to continue"), findsNothing);
  });
}
