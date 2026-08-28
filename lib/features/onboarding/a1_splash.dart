import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../mock/fixtures.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// A1 Splash and role select.
class A1Splash extends StatefulWidget {
  const A1Splash({super.key});

  @override
  State<A1Splash> createState() => _A1SplashState();
}

class _A1SplashState extends State<A1Splash> {
  ForgeRole _role = ForgeRole.talent;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: 20),
          const Align(alignment: Alignment.centerRight, child: DemoBadge()),
          const SizedBox(height: 10),
          Image.asset(kFlameMark, height: 132, fit: BoxFit.contain),
          const SizedBox(height: 8),
          GoldGradientText(
            "FORGE",
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: ForgeType.wordmark,
              fontWeight: FontWeight.bold,
              letterSpacing: 3,
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Container(
              width: 120,
              height: 1,
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: forge.goldGradient),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            "TALENT CONNECTIONS",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              fontWeight: FontWeight.w600,
              letterSpacing: 3.4,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: 26),
          ForgeCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Text(
                  "I am ...",
                  style: TextStyle(
                    fontFamily: ForgeType.displayFamily,
                    fontSize: 19,
                    fontWeight: FontWeight.bold,
                    color: forge.text,
                  ),
                ),
                const SizedBox(height: 12),
                for (final ForgeRole role in ForgeRole.values) ...<Widget>[
                  _RolePill(
                    role: role,
                    selected: role == _role,
                    onTap: () => setState(() => _role = role),
                  ),
                  if (role != ForgeRole.values.last)
                    const SizedBox(height: ForgeSpacing.gapCard),
                ],
                const SizedBox(height: ForgeSpacing.gapSection),
                _Continue(onTap: () => context.go("/create-profile")),
              ],
            ),
          ),
          const SizedBox(height: 26),
          Text(
            "Connecting Talent with Opportunity",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              fontWeight: FontWeight.w600,
              color: forge.text,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            "Provable trust for every connection",
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

class _RolePill extends StatelessWidget {
  const _RolePill({
    required this.role,
    required this.selected,
    required this.onTap,
  });

  final ForgeRole role;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(ForgeShape.ctaRadius),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        decoration: BoxDecoration(
          gradient: selected ? LinearGradient(colors: forge.goldGradient) : null,
          border: selected ? null : Border.all(color: forge.gold, width: 1.4),
          borderRadius: BorderRadius.circular(ForgeShape.ctaRadius),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              role.label,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.cardTitle,
                fontWeight: FontWeight.w700,
                color: selected ? Colors.white : forge.gold,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              role.blurb,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.caption,
                color: selected
                    ? Colors.white.withValues(alpha: 0.9)
                    : forge.textSub,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Continue extends StatelessWidget {
  const _Continue({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return InkWell(
      onTap: onTap,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Text(
            "Continue",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              fontWeight: FontWeight.w700,
              color: forge.gold,
            ),
          ),
          const SizedBox(width: 6),
          Icon(Icons.arrow_forward, size: 15, color: forge.gold),
        ],
      ),
    );
  }
}
