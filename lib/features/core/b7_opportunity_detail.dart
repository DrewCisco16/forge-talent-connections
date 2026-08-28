import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/demo_note.dart";
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
            if (o.engagement != null || o.vouchLevel != null ||
                o.evidence.isNotEmpty) ...<Widget>[
              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("The trust terms"),
              const SizedBox(height: ForgeSpacing.gapCard),
              ForgeCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    if (o.engagement != null)
                      _TermRow(
                        icon: Icons.school_outlined,
                        label: "Engagement",
                        value: o.engagement!,
                      ),
                    if (o.vouchLevel != null)
                      _TermRow(
                        icon: Icons.how_to_reg,
                        label: "To join",
                        value: o.vouchLevel!,
                      ),
                    if (o.evidence.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 6),
                      Text(
                        "Proof you can earn here",
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          fontWeight: FontWeight.w700,
                          color: forge.gold,
                        ),
                      ),
                      const SizedBox(height: 6),
                      for (final String e in o.evidence)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Icon(Icons.workspace_premium,
                                  size: 13, color: forge.gold),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  e,
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.caption,
                                    height: 1.3,
                                    color: forge.text,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ],
                ),
              ),
            ],
            const SizedBox(height: ForgeSpacing.gapSection),
            const SectionLabel("How a project works"),
            const SizedBox(height: ForgeSpacing.gapCard),
            ForgeCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  for (final (int i, String step) in <String>[
                    "A sponsor posts a defined project",
                    "Vouched members are invited, or ask to join",
                    "A team forms around complementary verified skills",
                    "Responsibilities and deliverables are recorded",
                    "Contributions are reviewed and checked",
                    "Outcomes are sealed when they pass",
                    "Contributors take portable proof of the work",
                    "That proof opens the next, bigger project",
                  ].indexed)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          SizedBox(
                            width: 22,
                            child: Text(
                              "${i + 1}",
                              style: TextStyle(
                                fontFamily: ForgeType.displayFamily,
                                fontSize: ForgeType.body,
                                fontWeight: FontWeight.w700,
                                color: forge.gold,
                              ),
                            ),
                          ),
                          Expanded(
                            child: Text(
                              step,
                              style: TextStyle(
                                fontFamily: ForgeType.bodyFamily,
                                fontSize: ForgeType.caption,
                                height: 1.35,
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
                  child: OutlineGoldButton(
                      label: "Save",
                      onPressed: () => demoNote(context,
                          "Saving arrives with your account on the backend.")),
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

class _TermRow extends StatelessWidget {
  const _TermRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, size: 15, color: forge.gold),
          const SizedBox(width: 9),
          Text(
            "$label: ",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              fontWeight: FontWeight.w700,
              color: forge.textSub,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.caption,
                height: 1.3,
                color: forge.text,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
