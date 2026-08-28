import "package:flutter/material.dart";
import "package:go_router/go_router.dart";

import "../../mock/fixtures.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/field_box.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// D3 Sign in.
class D3SignIn extends StatelessWidget {
  const D3SignIn({super.key});

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: 40),
          Image.asset(kFlameMark, height: 88, fit: BoxFit.contain),
          const SizedBox(height: 10),
          GoldGradientText(
            "FORGE",
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: 34,
              fontWeight: FontWeight.bold,
              letterSpacing: 2.5,
            ),
          ),
          const SizedBox(height: 6),
          // The brand is always the whole name: wordmark plus descriptor.
          Text(
            "TALENT CONNECTIONS",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              fontWeight: FontWeight.w600,
              letterSpacing: 2.8,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: 24),
          Text(
            "Welcome back.",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: ForgeType.screenTitle,
              fontWeight: FontWeight.bold,
              color: forge.text,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 6),
          const FieldBox(label: "Email", hint: "you@example.com"),
          const SizedBox(height: ForgeSpacing.gapCard),
          const FieldBox(label: "Password", hint: "••••••••"),
          const SizedBox(height: ForgeSpacing.gapCard),
          Align(
            alignment: Alignment.centerRight,
            child: Text(
              "Forgot password",
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.caption,
                fontWeight: FontWeight.w600,
                color: forge.gold,
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          GoldButton(
            label: "Sign In",
            onPressed: () => context.go("/dashboard"),
          ),
          const SizedBox(height: 8),
          Center(
            child: InkWell(
              onTap: () => context.go("/legal"),
              child: Text.rich(
                TextSpan(
                  children: <InlineSpan>[
                    TextSpan(
                      text: "By continuing you agree to the ",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.chip,
                        color: forge.textSub,
                      ),
                    ),
                    TextSpan(
                      text: "Terms & Privacy Policy",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.chip,
                        fontWeight: FontWeight.w700,
                        color: forge.gold,
                      ),
                    ),
                  ],
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection - 4),
          Row(
            children: <Widget>[
              Expanded(child: Divider(color: forge.strokeSoft)),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Text(
                  "or",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    color: forge.textSub,
                  ),
                ),
              ),
              Expanded(child: Divider(color: forge.strokeSoft)),
            ],
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          for (final String provider in <String>["Google", "Apple", "LinkedIn"])
            Padding(
              padding: const EdgeInsets.only(bottom: ForgeSpacing.gapCard),
              child: OutlineGoldButton(
                label: "Continue with $provider",
                onPressed: () => context.go("/dashboard"),
              ),
            ),
          const OutlineGoldButton(
            label: "Handshake · partnership in progress",
            // Never rendered as working before the partnership exists.
            onPressed: null,
          ),
          const SizedBox(height: 8),
          Text(
            "Demo sign-in: no real account is used. Production sign-in "
            "arrives with the backend over each provider's own secure "
            "sign-in system.",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.chip,
              height: 1.35,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Center(
            child: InkWell(
              onTap: () => context.go("/"),
              child: Text.rich(
                TextSpan(
                  children: <InlineSpan>[
                    TextSpan(
                      text: "New here? ",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.body,
                        color: forge.textSub,
                      ),
                    ),
                    TextSpan(
                      text: "Create an account",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.body,
                        fontWeight: FontWeight.w700,
                        color: forge.gold,
                      ),
                    ),
                  ],
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
