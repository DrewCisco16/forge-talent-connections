import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/fixtures.dart";
import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// D4 My profile and settings.
///
/// Also carries the demo controls. This build has no backend, so the scenario
/// switch is what makes the pending and denied paths reachable: changing it
/// re-renders every screen against a different set of outcomes.
class D4ProfileSettings extends ConsumerStatefulWidget {
  const D4ProfileSettings({super.key});

  @override
  ConsumerState<D4ProfileSettings> createState() => _D4ProfileSettingsState();
}

class _D4ProfileSettingsState extends ConsumerState<D4ProfileSettings> {
  bool _verificationAlerts = true;
  bool _matchSuggestions = true;

  Future<void> _confirmSignOut() async {
    final ForgeTheme forge = ForgeTheme.of(context);
    // Signing out is never instant: it is confirmed in a sheet first.
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: forge.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (BuildContext sheetContext) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(
              "Sign out of FORGE?",
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.cardTitle,
                fontWeight: FontWeight.w700,
                color: forge.text,
              ),
            ),
            const SizedBox(height: 18),
            SizedBox(
              width: double.infinity,
              child: TextButton(
                onPressed: () {
                  Navigator.of(sheetContext).pop();
                  context.go("/sign-in");
                },
                child: Text(
                  "Sign out",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontWeight: FontWeight.w700,
                    color: forge.red,
                  ),
                ),
              ),
            ),
            SizedBox(
              width: double.infinity,
              child: TextButton(
                onPressed: () => Navigator.of(sheetContext).pop(),
                child: Text(
                  "Cancel",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    color: forge.textSub,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    final DemoScenario scenario = ref.watch(demoScenarioProvider);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: 24),
          AsyncView<UserProfile>(
            value: ref.watch(profileProvider),
            pendingLabel: "Loading profile",
            builder: (UserProfile profile) => Column(
              children: <Widget>[
                Container(
                  width: 84,
                  height: 84,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(colors: forge.goldGradient),
                  ),
                  padding: const EdgeInsets.all(3),
                  child: Container(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: forge.surface2,
                      image: profile.avatarAsset == null
                          ? null
                          : DecorationImage(
                              image: AssetImage(profile.avatarAsset!),
                              fit: BoxFit.cover,
                            ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  profile.displayName,
                  style: TextStyle(
                    fontFamily: ForgeType.displayFamily,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: forge.text,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<TrustWalletSummary>(
            value: ref.watch(walletSummaryProvider),
            pendingLabel: "Loading record",
            builder: (TrustWalletSummary s) => InkWell(
              onTap: () => context.go("/trust-wallet"),
              child: ForgeCard(
                borderColor: forge.gold,
                child: Row(
                  children: <Widget>[
                    Icon(Icons.workspace_premium, size: 24, color: forge.gold),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            "Provable Track Record",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.cardTitle,
                              fontWeight: FontWeight.w700,
                              color: forge.text,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            "${s.deliverables} verified deliverables · 0 disputes",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              color: forge.textSub,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      "View",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        fontWeight: FontWeight.w700,
                        color: forge.gold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          const SectionLabel("Demo controls"),
          const SizedBox(height: 6),
          Text(
            "This build has no backend. Switch the fixture set to see how every screen behaves when checks pass, are still running, or fail.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.35,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          ForgeCard(
            borderColor: forge.violet.withValues(alpha: 0.5),
            child: Column(
              children: <Widget>[
                for (final DemoScenario s in DemoScenario.values)
                  InkWell(
                    onTap: () =>
                        ref.read(demoScenarioProvider.notifier).state = s,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Row(
                        children: <Widget>[
                          Icon(
                            s == scenario
                                ? Icons.radio_button_checked
                                : Icons.radio_button_unchecked,
                            size: 18,
                            color: s == scenario ? forge.violet : forge.textSub,
                          ),
                          const SizedBox(width: 11),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  s.label,
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.body,
                                    fontWeight: FontWeight.w700,
                                    color: forge.text,
                                  ),
                                ),
                                Text(
                                  s.blurb,
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.caption,
                                    color: forge.textSub,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          const SectionLabel("Account"),
          const SizedBox(height: ForgeSpacing.gapCard),
          for (final String item in <String>[
            "Personal info",
            "Skills & availability",
            "Payout methods",
          ])
            _Row(label: item, onTap: () {}),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Privacy & trust"),
          const SizedBox(height: ForgeSpacing.gapCard),
          _Row(label: "Profile visibility", trailing: "Public", onTap: () {}),
          _ToggleRow(
            label: "Verification alerts",
            value: _verificationAlerts,
            onChanged: (bool v) => setState(() => _verificationAlerts = v),
          ),
          _ToggleRow(
            label: "AI match suggestions",
            value: _matchSuggestions,
            onChanged: (bool v) => setState(() => _matchSuggestions = v),
          ),
          _Row(label: "Data & downloads", onTap: () => context.go("/export")),
          const SizedBox(height: ForgeSpacing.gapSection),
          _Row(
            label: "Veteran pathways",
            trailing: "Concept",
            onTap: () => context.go("/pathways"),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          InkWell(
            onTap: _confirmSignOut,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Text(
                "Sign out",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.cardTitle,
                  fontWeight: FontWeight.w700,
                  color: forge.red,
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.label, this.trailing, required this.onTap});

  final String label;
  final String? trailing;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 13),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.body,
                  color: forge.text,
                ),
              ),
            ),
            if (trailing != null)
              Text(
                trailing!,
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.caption,
                  color: forge.textSub,
                ),
              ),
            const SizedBox(width: 6),
            Icon(Icons.chevron_right, size: 17, color: forge.textSub),
          ],
        ),
      ),
    );
  }
}

class _ToggleRow extends StatelessWidget {
  const _ToggleRow({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.body,
                color: forge.text,
              ),
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: Colors.white,
            activeTrackColor: forge.gold,
            inactiveTrackColor: forge.strokeSoft,
          ),
        ],
      ),
    );
  }
}
