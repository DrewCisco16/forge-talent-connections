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

/// B7 Opportunity detail.
class B7OpportunityDetail extends ConsumerWidget {
  const B7OpportunityDetail({required this.opportunityId, super.key});

  final String opportunityId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: AsyncView<Opportunity>(
        value: ref.watch(opportunityProvider(opportunityId)),
        pendingLabel: "Loading project",
        builder: (Opportunity o) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            const SizedBox(height: ForgeSpacing.gapSection),
            Row(
              children: <Widget>[
                InkWell(
                  onTap: () => context.go("/opportunities"),
                  child: Icon(Icons.arrow_back, size: 19, color: forge.text),
                ),
                const SizedBox(width: 12),
                if (o.organizationStatus == VerificationStatus.verified)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: Icon(Icons.verified, size: 15, color: forge.green),
                  ),
                Expanded(
                  child: Text(
                    o.organization,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.body,
                      fontWeight: FontWeight.w600,
                      color: forge.text,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            Text(
              o.title,
              style: TextStyle(
                fontFamily: ForgeType.displayFamily,
                fontSize: ForgeType.screenTitle,
                fontWeight: FontWeight.bold,
                height: 1.15,
                color: forge.text,
              ),
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            Wrap(
              spacing: 7,
              runSpacing: 7,
              children: <Widget>[
                for (final String p in o.pills)
                  Container(
                    decoration: BoxDecoration(
                      color: forge.surface2,
                      border: Border.all(color: forge.strokeSoft),
                      borderRadius:
                          BorderRadius.circular(ForgeShape.pillRadius),
                    ),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 11, vertical: 5),
                    child: Text(
                      p,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        fontWeight: FontWeight.w600,
                        color: forge.text,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            Text(
              o.description,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.body,
                height: 1.4,
                color: forge.text,
              ),
            ),
            const SizedBox(height: ForgeSpacing.gapSection + 4),
            const SectionLabel("What you will deliver"),
            const SizedBox(height: ForgeSpacing.gapCard),
            for (final String d in o.deliverables)
              Padding(
                padding: const EdgeInsets.only(bottom: 9),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Padding(
                      padding: const EdgeInsets.only(top: 5),
                      child:
                          Icon(Icons.circle, size: 6, color: forge.gold),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        d,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.body,
                          height: 1.35,
                          color: forge.text,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: ForgeSpacing.gapSection),
            ForgeCard(
              borderColor: forge.green.withValues(alpha: 0.55),
              background: forge.green.withValues(alpha: 0.08),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Icon(Icons.shield_outlined, size: 17, color: forge.green),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          "Protected project",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.body,
                            fontWeight: FontWeight.w700,
                            color: forge.green,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          "Milestones, files, and payouts are governed. What you submit is what gets delivered, provably.",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.body,
                            height: 1.35,
                            color: forge.text,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            Row(
              children: <Widget>[
                Expanded(
                  child: OutlineGoldButton(label: "Save", onPressed: () {}),
                ),
                const SizedBox(width: ForgeSpacing.gapCard),
                Expanded(
                  child: GoldButton(
                    label: "Apply Now",
                    onPressed: () => context.go("/project-space"),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
