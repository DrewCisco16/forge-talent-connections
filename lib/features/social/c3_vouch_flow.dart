import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/social_action.dart";

/// C3 Vouch flow.
///
/// A vouch is a signed statement, so the confirming action is deliberate: it is
/// held rather than tapped, and the screen says plainly what is being attested.
class C3VouchFlow extends StatefulWidget {
  const C3VouchFlow({super.key});

  @override
  State<C3VouchFlow> createState() => _C3VouchFlowState();
}

class _C3VouchFlowState extends State<C3VouchFlow> {
  String _scope = "Both";
  bool _signed = false;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          InkWell(
            onTap: () => context.go("/feed"),
            child: Row(
              children: <Widget>[
                Icon(Icons.arrow_back, size: 17, color: forge.gold),
                const SizedBox(width: 8),
                Text(
                  "Maya Chen",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.body,
                    fontWeight: FontWeight.w600,
                    color: forge.gold,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Text(
            "Vouch for Maya",
            style: TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: ForgeType.heroTitle,
              fontWeight: FontWeight.bold,
              color: forge.text,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            "A vouch is not a like. It is your name attached to her work, permanently recorded.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              height: 1.4,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          ForgeCard(
            borderColor: forge.violet.withValues(alpha: 0.6),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  "You are attesting",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.cardTitle,
                    fontWeight: FontWeight.w700,
                    color: forge.text,
                  ),
                ),
                const SizedBox(height: 12),
                for (final String line in <String>[
                  "I worked with Maya directly",
                  "Her verified deliverables match what I saw",
                  "I would hire her again",
                ])
                  Padding(
                    padding: const EdgeInsets.only(bottom: 9),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Icon(Icons.check_circle, size: 15, color: forge.gold),
                        const SizedBox(width: 9),
                        Expanded(
                          child: Text(
                            line,
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.body,
                              height: 1.3,
                              color: forge.text,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Vouch scope"),
          const SizedBox(height: ForgeSpacing.gapCard),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              for (final String s in <String>["Skills", "Character", "Both"])
                _ScopeChip(
                  label: s,
                  selected: s == _scope,
                  onTap: () => setState(() => _scope = s),
                ),
            ],
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          ForgeCard(
            borderColor: forge.gold.withValues(alpha: 0.55),
            child: Text(
              "Your vouch history is public on your profile. Vouches that age well raise your own standing.",
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.body,
                height: 1.35,
                color: forge.text,
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          HoldToSignVouch(
            label: _signed ? "Vouch signed" : "Sign My Vouch",
            onCompleted: () => setState(() => _signed = true),
          ),
          const SizedBox(height: 10),
          Text(
            "Recorded with a tamper-evident signature",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _ScopeChip extends StatelessWidget {
  const _ScopeChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    // Selected scope uses a social-action surface; unselected stays neutral.
    if (selected) {
      return VibeButton(label: label, onPressed: onTap);
    }
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
      child: Container(
        decoration: BoxDecoration(
          border: Border.all(color: forge.strokeSoft),
          borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: ForgeType.bodyFamily,
            fontSize: ForgeType.body,
            fontWeight: FontWeight.w700,
            color: forge.textSub,
          ),
        ),
      ),
    );
  }
}
