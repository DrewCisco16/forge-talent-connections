import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// B2 Find opportunities.
class B2FindOpportunities extends ConsumerStatefulWidget {
  const B2FindOpportunities({super.key});

  @override
  ConsumerState<B2FindOpportunities> createState() =>
      _B2FindOpportunitiesState();
}

class _B2FindOpportunitiesState extends ConsumerState<B2FindOpportunities> {
  String _activeFilter = "Skills";

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    const List<String> filters = <String>[
      "Location",
      "Sponsor",
      "Skills",
      "Remote",
    ];

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          const HeroBand(
            title: "Find Opportunities",
            subtitle: "Projects sponsored by organizations near you",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Container(
            decoration: BoxDecoration(
              color: forge.surface2,
              borderRadius: BorderRadius.circular(ForgeShape.pillRadius),
              border: Border.all(color: forge.strokeSoft),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
            child: Row(
              children: <Widget>[
                Icon(Icons.search, size: 16, color: forge.textSub),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                  "Search projects",
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.body,
                    color: forge.textSub,
                  ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: <Widget>[
                for (final String f in filters)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: InkWell(
                      onTap: () => setState(() => _activeFilter = f),
                      borderRadius:
                          BorderRadius.circular(ForgeShape.pillRadius),
                      child: Container(
                        decoration: BoxDecoration(
                          color: f == _activeFilter
                              ? forge.goldDeep
                              : Colors.transparent,
                          border: Border.all(
                            color: f == _activeFilter
                                ? forge.goldDeep
                                : forge.strokeSoft,
                          ),
                          borderRadius:
                              BorderRadius.circular(ForgeShape.pillRadius),
                        ),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 13, vertical: 7),
                        child: Text(
                          f,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            fontWeight: FontWeight.w600,
                            color:
                                f == _activeFilter ? Colors.white : forge.textSub,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<List<Opportunity>>(
            value: ref.watch(opportunitiesProvider),
            pendingLabel: "Searching",
            builder: (List<Opportunity> items) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    // Expanded lets the label wrap at large text sizes
                    // instead of colliding with the count.
                    const Expanded(child: SectionLabel("Search results")),
                    const SizedBox(width: 8),
                    Text(
                      "${items.length} projects",
                      maxLines: 1,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        color: forge.textSub,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: ForgeSpacing.gapCard),
                for (final Opportunity o in items) ...<Widget>[
                  OpportunityCard(
                    opportunity: o,
                    onTap: () => context.go("/opportunity/${o.id}"),
                  ),
                  const SizedBox(height: ForgeSpacing.gapCard),
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

/// A project card as it appears in search results.
class OpportunityCard extends StatelessWidget {
  const OpportunityCard({
    required this.opportunity,
    required this.onTap,
    super.key,
  });

  final Opportunity opportunity;
  final VoidCallback onTap;

  Color _tone(ForgeTheme forge, TechTagTone tone) => switch (tone) {
        TechTagTone.gold => forge.gold,
        TechTagTone.green => forge.green,
        TechTagTone.cyan => forge.cyan,
        TechTagTone.violet => forge.violet,
      };

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
      child: ForgeCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              opportunity.title,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: forge.text,
              ),
            ),
            const SizedBox(height: 6),
            Row(
              children: <Widget>[
                if (opportunity.organizationStatus ==
                    VerificationStatus.verified) ...<Widget>[
                  Icon(Icons.verified, size: 13, color: forge.green),
                  const SizedBox(width: 5),
                ],
                Flexible(
                  child: Text(
                    opportunity.organizationStatus ==
                            VerificationStatus.verified
                        ? "${opportunity.organizationKind} · Verified organization"
                        : "${opportunity.organizationKind} · Verification pending",
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      color: opportunity.organizationStatus ==
                              VerificationStatus.verified
                          ? forge.green
                          : forge.textSub,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            Text(
              opportunity.description,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.body,
                height: 1.35,
                color: forge.text,
              ),
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            Wrap(
              spacing: 7,
              runSpacing: 7,
              children: <Widget>[
                for (final TechTag t in opportunity.tags)
                  Container(
                    decoration: BoxDecoration(
                      color: _tone(forge, t.tone).withValues(alpha: 0.13),
                      border: Border.all(
                        color: _tone(forge, t.tone).withValues(alpha: 0.5),
                      ),
                      borderRadius:
                          BorderRadius.circular(ForgeShape.pillRadius),
                    ),
                    padding:
                        const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                    child: Text(
                      t.label,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.chip,
                        fontWeight: FontWeight.w700,
                        color: _tone(forge, t.tone),
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
