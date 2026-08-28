import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/status_chip.dart";

/// B5 Trust wallet.
class B5TrustWallet extends ConsumerWidget {
  const B5TrustWallet({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: 24),
          GoldGradientText(
            "Trust Wallet",
            style: const TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: ForgeType.screenTitle,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            "Everything here survived verification",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<TrustWalletSummary>(
            value: ref.watch(walletSummaryProvider),
            pendingLabel: "Loading wallet",
            builder: (TrustWalletSummary s) => ForgeCard(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: <Widget>[
                  _Stat(value: s.deliverables, label: "Deliverables"),
                  _Stat(value: s.credentials, label: "Credentials"),
                  _Stat(value: s.vouches, label: "Vouches"),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          const SectionLabel("Credentials"),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<List<Credential>>(
            value: ref.watch(credentialsProvider),
            pendingLabel: "Loading credentials",
            builder: (List<Credential> credentials) => ForgeCard(
              child: Column(
                children: <Widget>[
                  for (final Credential c in credentials)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              c.title,
                              style: TextStyle(
                                fontFamily: ForgeType.bodyFamily,
                                fontSize: ForgeType.body,
                                color: forge.text,
                              ),
                            ),
                          ),
                          StatusChip(status: c.status, dense: true),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Vouched by"),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<List<Vouch>>(
            value: ref.watch(vouchesProvider),
            pendingLabel: "Loading vouches",
            builder: (List<Vouch> vouches) => InkWell(
              onTap: () => context.go("/vouch"),
              child: ForgeCard(
                child: Row(
                  children: <Widget>[
                    SizedBox(
                      width: 26.0 * vouches.length + 12,
                      height: 34,
                      child: Stack(
                        children: <Widget>[
                          for (int i = 0; i < vouches.length; i++)
                            Positioned(
                              left: i * 24,
                              child: Container(
                                width: 34,
                                height: 34,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                    color: ForgeColors.navyDeep,
                                    width: 2,
                                  ),
                                  image: DecorationImage(
                                    image: AssetImage(vouches[i].fromAvatar),
                                    fit: BoxFit.cover,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            "${vouches.length} people signed their name to Drew's work",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              fontWeight: FontWeight.w600,
                              color: forge.text,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            "Tap to read each vouch",
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
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          GoldButton(
            label: "Share Verified Profile",
            onPressed: () => context.go("/export"),
          ),
          const SizedBox(height: 8),
          Text(
            "The link carries only facts that passed a check.",
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

class _Stat extends StatelessWidget {
  const _Stat({required this.value, required this.label});

  final int value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Column(
      children: <Widget>[
        GoldGradientText(
          "$value",
          style: const TextStyle(
            fontFamily: ForgeType.displayFamily,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: TextStyle(
            fontFamily: ForgeType.bodyFamily,
            fontSize: ForgeType.caption,
            color: forge.textSub,
          ),
        ),
      ],
    );
  }
}
