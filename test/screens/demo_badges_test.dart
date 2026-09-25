import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/app/widget_gallery.dart";
import "package:forge_talent_connections/features/core/b4_credentials.dart";
import "package:forge_talent_connections/features/core/b5_trust_wallet.dart";
import "package:forge_talent_connections/features/onboarding/a4_veteran_verification.dart";
import "package:forge_talent_connections/features/onboarding/legal_terms.dart";
import "package:forge_talent_connections/features/social/c6_rewards.dart";
import "package:forge_talent_connections/features/trust/d1_export_certificate.dart";
import "package:forge_talent_connections/features/core/ai_assistant.dart";
import "package:forge_talent_connections/features/core/talent_signature.dart";
import "package:forge_talent_connections/features/social/talent_stories.dart";
import "package:forge_talent_connections/features/trust/d5_veteran_roads.dart";
import "package:forge_talent_connections/features/trust/seal_check.dart";
import "package:forge_talent_connections/features/trust/trust_technology.dart";
import "package:forge_talent_connections/theme/forge_theme.dart";
import "package:forge_talent_connections/widgets/section_label.dart";

/// Every verification-heavy screen carries the persistent sample-data
/// disclosure. Demo fixtures must never read as live verification.
void main() {
  final Map<String, Widget> screens = <String, Widget>{
    "A4 Veteran Verification": const A4VeteranVerification(),
    "B4 Credentials": const B4Credentials(),
    "B5 Trust Wallet": const B5TrustWallet(),
    "C6 Rewards": const C6Rewards(),
    "D1 Export": const D1ExportCertificate(),
    "D5 Veteran Roads": const D5VeteranRoads(),
    "AI Assistant": const AiAssistant(),
    "Talent Stories": const TalentStories(),
    "Talent Signature": const TalentSignatureScreen(),
    "Legal Terms": const LegalTerms(),
    "Seal Check": const SealCheck(),
    "Trust Technology": const TrustTechnology(),
    "Widget Gallery": const WidgetGallery(),
  };

  for (final MapEntry<String, Widget> entry in screens.entries) {
    testWidgets("${entry.key} shows the demo disclosure", (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(440, 4200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme: buildForgeTheme(),
            home: MediaQuery(
              data: const MediaQueryData(
                size: Size(440, 4200),
                disableAnimations: true,
              ),
              child: entry.value,
            ),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));
      expect(
        find.byType(DemoBadge),
        findsWidgets,
        reason: "${entry.key} must carry the DEMO badge",
      );
    });
  }
}
