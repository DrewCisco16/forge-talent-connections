import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/seal_card.dart";
import "../../widgets/section_label.dart";

/// Authentic service colours. These are exempt from theming and must not be
/// tinted, dimmed, or harmonised with the palette.
///
/// TODO(licensed-art): the flag blocks below are solid-colour placeholders.
/// Real flag artwork, the Eagle Globe and Anchor, and other service marks carry
/// usage rules and need licensed sources plus professional review before any
/// public release.
const Map<String, Color> _branchColors = <String, Color>{
  "usmc": Color(0xFFB3141F),
  "usa": Color(0xFF4B5320),
  "usn": Color(0xFF000080),
  "usaf": Color(0xFF00308F),
  "uscg": Color(0xFFE4652B),
  "ussf": Color(0xFF1B2A4A),
};

/// A4 Veteran verification.
class A4VeteranVerification extends ConsumerStatefulWidget {
  const A4VeteranVerification({super.key});

  @override
  ConsumerState<A4VeteranVerification> createState() =>
      _A4VeteranVerificationState();
}

class _A4VeteranVerificationState extends ConsumerState<A4VeteranVerification> {
  String _selected = "usmc";

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          const Align(alignment: Alignment.centerRight, child: DemoBadge()),
          const SizedBox(height: 8),
          HeroBand(
            title: "Veteran Verification",
            subtitle: "Seal your service record so it can be trusted anywhere",
            onBack: () => context.go("/choose-avatar"),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<List<ServiceBranch>>(
            value: ref.watch(branchesProvider),
            pendingLabel: "Loading branches",
            builder: (List<ServiceBranch> branches) {
              final ServiceBranch featured = branches.firstWhere(
                (ServiceBranch b) => b.id == _selected,
                orElse: () => branches.first,
              );
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  ForgeCard(
                    borderColor: _branchColors[featured.id],
                    borderWidth: 2,
                    child: Column(
                      children: <Widget>[
                        _FlagBlock(id: featured.id, height: 74),
                        const SizedBox(height: 12),
                        Text(
                          featured.name,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontFamily: ForgeType.displayFamily,
                            fontSize: 19,
                            fontWeight: FontWeight.bold,
                            color: _branchColors[featured.id],
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          featured.motto,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.body,
                            fontStyle: FontStyle.italic,
                            color: forge.textSub,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: ForgeSpacing.gapSection + 6),
                  const SectionLabel("Branch of service"),
                  const SizedBox(height: 6),
                  Text(
                    "Choose the flag you represent",
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.body,
                      color: forge.textSub,
                    ),
                  ),
                  const SizedBox(height: ForgeSpacing.gapCard),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: branches.length,
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 3,
                          mainAxisSpacing: 10,
                          crossAxisSpacing: 10,
                          childAspectRatio: 0.95,
                        ),
                    itemBuilder: (BuildContext context, int i) {
                      final ServiceBranch b = branches[i];
                      final bool selected = b.id == _selected;
                      return InkWell(
                        onTap: () => setState(() => _selected = b.id),
                        borderRadius: BorderRadius.circular(
                          ForgeShape.cardRadius,
                        ),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 160),
                          decoration: BoxDecoration(
                            color: forge.surface,
                            borderRadius: BorderRadius.circular(
                              ForgeShape.cardRadius,
                            ),
                            border: Border.all(
                              color: selected
                                  ? _branchColors[b.id]!
                                  : forge.strokeSoft,
                              width: selected ? 2 : 1,
                            ),
                          ),
                          padding: const EdgeInsets.all(9),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: <Widget>[
                              _FlagBlock(id: b.id, height: 34),
                              const SizedBox(height: 8),
                              Text(
                                b.shortName,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.caption,
                                  fontWeight: FontWeight.w700,
                                  color: forge.text,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          const SealCard(
            text: "Once verified, your service record is sealed and tamper-evident. Collaborators see the seal, never your documents.",
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          GoldButton(
            label: "Verify My Service",
            onPressed: () => context.go("/elevator-pitch"),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

/// The branch's service flag.
///
/// Shows the real flag artwork from `assets/flags/{id}.png` the moment the
/// file exists. Until then it falls back to a block in the branch's authentic flag
/// colour - never a themed or invented substitute. Flag colours are exempt
/// from theming.
class _FlagBlock extends StatelessWidget {
  const _FlagBlock({required this.id, required this.height});

  final String id;
  final double height;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(6),
      child: Image.asset(
        "assets/flags/$id.png",
        height: height,
        fit: BoxFit.cover,
        errorBuilder: (BuildContext context, Object error, StackTrace? stack) {
          // Until the real flag artwork is supplied, the card shows the
          // branch initials on its authentic field colour. Never an invented
          // rendition of official heraldry.
          return Container(
            height: height,
            width: height * 1.5,
            color: _branchColors[id],
            alignment: Alignment.center,
            child: Text(
              id.toUpperCase(),
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: height * 0.30,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.5,
                color: Colors.white.withValues(alpha: 0.92),
              ),
            ),
          );
        },
      ),
    );
  }
}
