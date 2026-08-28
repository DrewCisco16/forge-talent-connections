import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/confetti_burst.dart";
import "../../widgets/gold_button.dart";
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
                  "I would onboard her again",
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
          // The burst plays over the hold control the moment the sweep
          // completes. Celebration only: it ignores pointers, plays once,
          // and paints nothing under reduced motion.
          Stack(
            clipBehavior: Clip.none,
            children: <Widget>[
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
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
                ],
              ),
              Positioned(
                left: 0,
                right: 0,
                top: -230,
                bottom: 0,
                child: ConfettiBurst(
                  play: _signed,
                  colors: <Color>[
                    forge.gold,
                    forge.violet,
                    forge.green,
                    forge.cyan,
                    forge.coral,
                  ],
                ),
              ),
            ],
          ),
          if (_signed) ...<Widget>[
            const SizedBox(height: ForgeSpacing.gapSection),
            ForgeCard(
              borderColor: forge.gold,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Icon(Icons.celebration_outlined,
                          size: 18, color: forge.gold),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          "Your vouch is sealed",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.cardTitle,
                            fontWeight: FontWeight.w700,
                            color: forge.text,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Your name now stands behind Maya's work. Reward "
                    "points for this vouch are awarded by the backend "
                    "once the vouch verifies — never by the tap itself.",
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      height: 1.35,
                      color: forge.textSub,
                    ),
                  ),
                  const SizedBox(height: 10),
                  OutlineGoldButton(
                    label: "View Rewards & Referrals",
                    onPressed: () => context.go("/rewards"),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          const SectionLabel("How vouching is governed"),
          const SizedBox(height: 6),
          Text(
            "Entry comes through accountable trust. Standing is earned "
            "through your own work.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              fontWeight: FontWeight.w700,
              height: 1.35,
              color: forge.gold,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          ForgeCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                for (final (String q, String a) in <(String, String)>[
                  (
                    "Who can vouch",
                    "Verified members, and community partners such as "
                        "faculty, program staff, and veteran organizations.",
                  ),
                  (
                    "What a vouch attests",
                    "The signed statements above — never a favor. The basis "
                        "is disclosed on the vouch itself.",
                  ),
                  (
                    "How many",
                    "Active vouches per member are limited, and the ledger "
                        "of vouches you have given is public.",
                  ),
                  (
                    "Misuse",
                    "A vouch can be revoked; revocation is recorded. Abuse "
                        "costs the voucher their own standing.",
                  ),
                  (
                    "Appeals",
                    "Any refusal or revocation can be sent to a person for "
                        "review.",
                  ),
                  (
                    "Your first vouch",
                    "No network yet? A sealed verification counts as one "
                        "vouch, and community partners can vouch for their "
                        "own members.",
                  ),
                  (
                    "What outweighs what",
                    "Earned, verified work always ends up counting for more "
                        "than who you knew when you arrived.",
                  ),
                ]) ...<Widget>[
                  Text(
                    q,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      fontWeight: FontWeight.w700,
                      color: forge.text,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text(
                      a,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        height: 1.35,
                        color: forge.textSub,
                      ),
                    ),
                  ),
                ],
              ],
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
