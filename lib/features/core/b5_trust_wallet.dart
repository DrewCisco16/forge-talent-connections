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
          const Align(alignment: Alignment.centerRight, child: DemoBadge()),
          const SizedBox(height: 8),
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
                children: <Widget>[
                  Expanded(
                    child: _Stat(value: s.deliverables, label: "Deliverables"),
                  ),
                  Expanded(
                    child: _Stat(value: s.credentials, label: "Credentials"),
                  ),
                  Expanded(
                    child: _Stat(value: s.vouches, label: "Vouches"),
                  ),
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
            builder: (List<Vouch> vouches) {
              // The headline count is the backend's, not a count of however
              // many vouches this screen happened to load. Showing a different
              // number here than in the summary strip would be a contradiction
              // in a product whose whole claim is that its numbers hold up.
              final int total =
                  ref.watch(walletSummaryProvider).valueOrNull?.vouches ??
                  vouches.length;
              final List<Vouch> shown = vouches.take(5).toList();
              return InkWell(
                onTap: () => context.go("/vouch"),
                child: ForgeCard(
                  child: Row(
                    children: <Widget>[
                      SizedBox(
                        width: 26.0 * shown.length + 12,
                        height: 34,
                        child: Stack(
                          children: <Widget>[
                            for (int i = 0; i < shown.length; i++)
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
                                      image: AssetImage(shown[i].fromAvatar),
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
                              "$total people signed their name to Drew's work",
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
              );
            },
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // A vouch carries its basis on its face: a shared verified project
          // outweighs acquaintance, and the difference is shown, not hidden.
          AsyncView<List<Vouch>>(
            value: ref.watch(vouchesProvider),
            pendingLabel: "Loading vouch detail",
            builder: (List<Vouch> vouches) {
              final Vouch v = vouches.first;
              return ForgeCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      "“${v.text}”",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.body,
                        height: 1.4,
                        fontStyle: FontStyle.italic,
                        color: forge.text,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      "- ${v.fromName}, ${v.signedOn}",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        color: forge.textSub,
                      ),
                    ),
                    if (v.basis != null) ...<Widget>[
                      const SizedBox(height: 8),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Icon(
                            v.basisStatus.isProven
                                ? Icons.verified_outlined
                                : Icons.person_outline,
                            size: 13,
                            color: v.basisStatus.isProven
                                ? forge.gold
                                : forge.textSub,
                          ),
                          const SizedBox(width: 5),
                          Expanded(
                            child: Text(
                              "Basis: ${v.basis}"
                              "${v.basisStatus.isProven ? "" : " · carries less weight"}",
                              style: TextStyle(
                                fontFamily: ForgeType.bodyFamily,
                                fontSize: ForgeType.chip,
                                fontWeight: FontWeight.w600,
                                color: v.basisStatus.isProven
                                    ? forge.gold
                                    : forge.textSub,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          InkWell(
            onTap: () => context.go("/vouch"),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Icon(Icons.gavel_outlined, size: 13, color: forge.gold),
                const SizedBox(width: 6),
                Flexible(
                  child: Text(
                    "How vouching is governed",
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      fontWeight: FontWeight.w700,
                      color: forge.gold,
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                Icon(Icons.arrow_forward, size: 12, color: forge.gold),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Vouches Drew has given"),
          const SizedBox(height: 6),
          Text(
            "This ledger is public. A vouch spends your own credibility, so "
            "everyone can see how each name was spent.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.35,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          AsyncView<List<GivenVouch>>(
            value: ref.watch(givenVouchesProvider),
            pendingLabel: "Loading ledger",
            builder: (List<GivenVouch> given) => ForgeCard(
              child: Column(
                children: <Widget>[
                  for (final GivenVouch g in given)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Container(
                            width: 30,
                            height: 30,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              image: DecorationImage(
                                image: AssetImage(g.toAvatar),
                                fit: BoxFit.cover,
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  "${g.toName} · ${g.signedOn}",
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.body,
                                    fontWeight: FontWeight.w600,
                                    color: forge.text,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  g.basis,
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
                ],
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
          const SizedBox(height: ForgeSpacing.gapSection),
          InkWell(
            onTap: () => context.go("/trust-technology"),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Icon(Icons.shield_outlined, size: 14, color: forge.gold),
                const SizedBox(width: 6),
                Flexible(
                  child: Text(
                    "Built on patent-pending technology",
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      fontWeight: FontWeight.w700,
                      color: forge.gold,
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                Icon(Icons.arrow_forward, size: 12, color: forge.gold),
              ],
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
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.center,
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
