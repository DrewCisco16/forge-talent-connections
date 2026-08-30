import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/features/core/ai_assistant.dart";
import "package:forge_talent_connections/features/core/b3_proof_builder.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";

/// The two founder-named AI surfaces hold their honest frames: the Proof
/// Builder assembles a Verified Portfolio from verified records only, and
/// the AI Assistant is a scripted sample that names its production home
/// (Google Cloud Vertex AI), its premium research capability, and its
/// limits.
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

  testWidgets("the Proof Builder carries the founder's names and frame", (
    WidgetTester tester,
  ) async {
    await pumpScreen(tester, const B3ProofBuilder());
    expect(find.text("Proof Builder"), findsOneWidget);
    expect(
      find.text("Your Verified Portfolio, assembled from proof"),
      findsOneWidget,
    );
    expect(find.text("Assemble Verified Portfolio"), findsOneWidget);
    // The verbatim governance banner, updated per the founder's rename.
    expect(
      find.text(
        "Your Verified Portfolio only claims what is verified. No "
        "invented roles, dates, or numbers, ever.",
      ),
      findsOneWidget,
    );
    // Production home named honestly.
    expect(find.textContaining("Google Cloud Vertex AI"), findsOneWidget);
  });

  testWidgets("the AI Assistant is honest about what it is and is not", (
    WidgetTester tester,
  ) async {
    await pumpScreen(tester, const AiAssistant());
    expect(find.text("AI Assistant"), findsWidgets);
    // Premium research capability, named.
    expect(find.text("PREMIUM · SCHOLARLY RESEARCH"), findsOneWidget);
    expect(find.text("Scholarly research · Premium"), findsOneWidget);
    // Research is registry-first: only records that exist.
    expect(
      find.textContaining("summarises only records that exist"),
      findsOneWidget,
    );
    // Sample results are labelled samples, never fabricated citations.
    expect(find.textContaining("Sample registry record 1"), findsOneWidget);
    // The assistant never writes to a record; two-human standard holds.
    expect(find.textContaining("I never write to your record"), findsOneWidget);
    // Production home and demo honesty.
    expect(find.textContaining("Google Cloud Vertex AI"), findsOneWidget);
    expect(find.textContaining("scripted sample"), findsWidgets);
  });
}
