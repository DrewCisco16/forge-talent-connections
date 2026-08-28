import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/score_ring.dart";
import "../../widgets/section_label.dart";

/// B6 AI match, where a person decides.
///
/// Nothing on this screen decides anything. The score arrives from the backend,
/// the human-review framing is always present, and the transparency accordion
/// states plainly what the suggestion cannot do.
class B6AiMatch extends ConsumerStatefulWidget {
  const B6AiMatch({required this.opportunityId, super.key});

  final String opportunityId;

  @override
  ConsumerState<B6AiMatch> createState() => _B6AiMatchState();
}

class _B6AiMatchState extends ConsumerState<B6AiMatch> {
  bool _usedExpanded = false;
  bool _neverExpanded = true;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: AsyncView<MatchSuggestion>(
        value: ref.watch(matchSuggestionProvider(widget.opportunityId)),
        pendingLabel: "Loading suggestion",
        builder: (MatchSuggestion match) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            const SizedBox(height: ForgeSpacing.gapSection),
            InkWell(
              onTap: () => context.go("/opportunity/${match.opportunityId}"),
              child: Row(
                children: <Widget>[
                  Icon(Icons.arrow_back, size: 17, color: forge.gold),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      match.opportunityTitle,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.body,
                        fontWeight: FontWeight.w600,
                        color: forge.gold,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            ForgeCard(
              borderColor: forge.gold,
              borderWidth: 1.5,
              child: Column(
                children: <Widget>[
                  ScoreRing(value: match.score, label: match.headline),
                  const SizedBox(height: ForgeSpacing.gapSection),
                  // Required copy. Ships verbatim.
                  Text(
                    "Suggested, not decided. A person reviews every match before anything is final.",
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.body,
                      height: 1.35,
                      fontWeight: FontWeight.w600,
                      color: forge.text,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: ForgeSpacing.gapSection + 4),
            const SectionLabel("Why this is suggested"),
            const SizedBox(height: ForgeSpacing.gapCard),
            ForgeCard(
              child: Column(
                children: <Widget>[
                  for (final MatchFactor f in match.factors)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Icon(
                              Icons.circle,
                              size: 8,
                              color: f.kind == MatchFactorKind.supporting
                                  ? forge.green
                                  : forge.coral,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              f.text,
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
            // Required copy. Ships verbatim.
            const BannerNote(
              text:
                  "Borderline factors go to a human reviewer. You will see who reviewed and when.",
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            _Accordion(
              title: "What the suggestion used",
              expanded: _usedExpanded,
              onToggle: () => setState(() => _usedExpanded = !_usedExpanded),
              body:
                  "Verified deliverables, cleared credentials, stated availability, and the project's own requirements.",
            ),
            const SizedBox(height: ForgeSpacing.gapCard),
            _Accordion(
              title: "What it can never do",
              expanded: _neverExpanded,
              onToggle: () => setState(() => _neverExpanded = !_neverExpanded),
              // Required copy. Ships verbatim.
              body:
                  "It cannot accept, reject, pay, or publish anything. Suggestions never change your record. Only verified actions by people do.",
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            Row(
              children: <Widget>[
                Expanded(
                  child: OutlineGoldButton(
                    label: "Pass",
                    onPressed: () => context.go("/opportunities"),
                  ),
                ),
                const SizedBox(width: ForgeSpacing.gapCard),
                Expanded(
                  child: GoldButton(
                    label: "Apply to Project",
                    onPressed: () => context.go(
                      "/opportunity/${match.opportunityId}",
                    ),
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

class _Accordion extends StatelessWidget {
  const _Accordion({
    required this.title,
    required this.body,
    required this.expanded,
    required this.onToggle,
  });

  final String title;
  final String body;
  final bool expanded;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return ForgeCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          InkWell(
            onTap: onToggle,
            child: Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    title,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.cardTitle,
                      fontWeight: FontWeight.w700,
                      color: forge.text,
                    ),
                  ),
                ),
                Icon(
                  expanded ? Icons.expand_less : Icons.expand_more,
                  size: 19,
                  color: forge.textSub,
                ),
              ],
            ),
          ),
          if (expanded) ...<Widget>[
            const SizedBox(height: 10),
            Text(
              body,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.body,
                height: 1.4,
                color: forge.text,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
