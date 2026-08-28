import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/credential_card.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// B4 Verified credentials.
class B4Credentials extends ConsumerWidget {
  const B4Credentials({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          const HeroBand(
            title: "Verified Credentials",
            subtitle: "Sealed so employers can trust them anywhere",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<List<Credential>>(
            value: ref.watch(credentialsProvider),
            pendingLabel: "Loading credentials",
            builder: (List<Credential> credentials) {
              final int verified = credentials
                  .where((Credential c) => c.status.isProven)
                  .length;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  ForgeCard(
                    child: Row(
                      children: <Widget>[
                        Icon(Icons.shield_outlined, size: 26, color: forge.gold),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                "$verified of ${credentials.length} verified",
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.cardTitle,
                                  fontWeight: FontWeight.w700,
                                  color: forge.text,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                "Employers see only what the check proved.",
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
                  const SizedBox(height: ForgeSpacing.gapSection),
                  GoldButton(
                    label: "Verify All Credentials",
                    onPressed: () {},
                  ),
                  const SizedBox(height: ForgeSpacing.gapSection),
                  for (final Credential c in credentials) ...<Widget>[
                    CredentialCard(
                      title: c.title,
                      status: c.status,
                      meta: c.metaLine,
                      actionLabel: c.status.isProven ? null : "Verify Credential",
                      onAction: c.status.isProven ? null : () {},
                    ),
                    const SizedBox(height: ForgeSpacing.gapCard),
                  ],
                ],
              );
            },
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
