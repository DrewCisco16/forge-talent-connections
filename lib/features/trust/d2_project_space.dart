import "dart:ui" show PathMetric;

import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/demo_note.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/status_chip.dart";

/// D2 Project space.
///
/// A failed deliverable locks export downstream, and the screen says so at the
/// point where the person would otherwise expect to proceed.
class D2ProjectSpace extends ConsumerWidget {
  const D2ProjectSpace({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: AsyncView<ProjectSpace>(
        value: ref.watch(projectSpaceProvider),
        pendingLabel: "Loading project",
        builder: (ProjectSpace space) {
          final int approved = space.milestones
              .where((Milestone m) => m.status.isProven)
              .length;
          final bool blocked = space.deliverables
              .any((Deliverable d) => d.status.blocksRelease);

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              const SizedBox(height: ForgeSpacing.gapSection),
              HeroBand(
                title: space.projectName,
                subtitle: space.organization,
              ),
              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Milestones"),
              const SizedBox(height: ForgeSpacing.gapCard),
              ForgeCard(
                child: Column(
                  children: <Widget>[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        value: approved / space.milestones.length,
                        minHeight: 6,
                        backgroundColor: forge.strokeSoft,
                        valueColor:
                            AlwaysStoppedAnimation<Color>(forge.gold),
                      ),
                    ),
                    const SizedBox(height: 14),
                    for (final Milestone m in space.milestones)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          children: <Widget>[
                            Expanded(
                              child: Text(
                                m.name,
                                style: TextStyle(
                                  fontFamily: ForgeType.bodyFamily,
                                  fontSize: ForgeType.body,
                                  color: forge.text,
                                ),
                              ),
                            ),
                            StatusChip(status: m.status, dense: true),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Deliverables"),
              const SizedBox(height: ForgeSpacing.gapCard),
              for (final Deliverable d in space.deliverables)
                Container(
                  margin: const EdgeInsets.only(bottom: ForgeSpacing.gapCard),
                  decoration: BoxDecoration(
                    color: forge.surface,
                    borderRadius:
                        BorderRadius.circular(ForgeShape.cardRadius),
                    border: Border.all(
                      color: d.status.blocksRelease
                          ? forge.red
                          : forge.strokeSoft,
                    ),
                  ),
                  padding: const EdgeInsets.all(ForgeSpacing.cardPad),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              d.name,
                              style: TextStyle(
                                fontFamily: ForgeType.bodyFamily,
                                fontSize: ForgeType.body,
                                fontWeight: FontWeight.w600,
                                color: forge.text,
                              ),
                            ),
                          ),
                          StatusChip(status: d.status, dense: true),
                        ],
                      ),
                      if (d.submittedOn != null || d.failureReason != null) ...<Widget>[
                        const SizedBox(height: 6),
                        Text(
                          d.failureReason ?? "Submitted ${d.submittedOn}",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            color: d.failureReason != null
                                ? forge.red
                                : forge.textSub,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              DottedDropZone(
                  onTap: () => demoNote(context,
                      "Submitted files are checked by the backend. This demo "
                      "renders the outcomes.")),
              if (blocked) ...<Widget>[
                const SizedBox(height: ForgeSpacing.gapSection),
                const BannerNote(
                  tone: BannerTone.denial,
                  text:
                      "A deliverable did not pass its check. Export stays blocked until it is resolved.",
                ),
                const SizedBox(height: ForgeSpacing.gapCard),
                InkWell(
                  onTap: () => context.go("/export"),
                  child: Text(
                    "See what is blocked",
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      fontWeight: FontWeight.w700,
                      color: forge.gold,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Team health"),
              const SizedBox(height: 6),
              Text(
                "Integrity for the people, parallel to integrity for the "
                "files. Check-ins are private to you and a human reviewer.",
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.caption,
                  height: 1.35,
                  color: forge.textSub,
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapCard),
              if (space.teamNorms.isNotEmpty)
                ForgeCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        "Working agreements · accepted at kickoff",
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          fontWeight: FontWeight.w700,
                          color: forge.text,
                        ),
                      ),
                      const SizedBox(height: 8),
                      for (final String norm in space.teamNorms)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Icon(Icons.handshake_outlined,
                                  size: 13, color: forge.gold),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  norm,
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
                  ),
                ),
              if (space.checkInPrompt != null) ...<Widget>[
                const SizedBox(height: ForgeSpacing.gapCard),
                _CheckInCard(prompt: space.checkInPrompt!),
              ],
              const SizedBox(height: ForgeSpacing.gapCard),
              InkWell(
                onTap: () => demoNote(context,
                    "Flag recorded privately. A person will follow up."),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Icon(Icons.flag_outlined, size: 14, color: forge.textSub),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        "Flag a concern — it goes to a person, quietly",
                        maxLines: 2,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          fontWeight: FontWeight.w600,
                          color: forge.textSub,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Activity"),
              const SizedBox(height: ForgeSpacing.gapCard),
              for (final String a in space.activity)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Padding(
                        padding: const EdgeInsets.only(top: 5),
                        child: Icon(Icons.circle, size: 5, color: forge.textSub),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          a,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            color: forge.textSub,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }
}

/// The private weekly check-in. Selecting an option is local to the demo;
/// in production the answer goes only to the person and a human reviewer.
class _CheckInCard extends StatefulWidget {
  const _CheckInCard({required this.prompt});

  final String prompt;

  @override
  State<_CheckInCard> createState() => _CheckInCardState();
}

class _CheckInCardState extends State<_CheckInCard> {
  String? _choice;

  static const List<(IconData, String)> _options = <(IconData, String)>[
    (Icons.thumb_up_alt_outlined, "Going well"),
    (Icons.error_outline, "Needs attention"),
    (Icons.record_voice_over_outlined, "Talk to someone"),
  ];

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return ForgeCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(Icons.lock_outline, size: 13, color: forge.textSub),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  "Private check-in",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    fontWeight: FontWeight.w700,
                    color: forge.text,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            widget.prompt,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              height: 1.3,
              color: forge.text,
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              for (final (IconData icon, String label) in _options)
                InkWell(
                  onTap: () => setState(() => _choice = label),
                  borderRadius:
                      BorderRadius.circular(ForgeShape.pillRadius),
                  child: Container(
                    decoration: BoxDecoration(
                      color: _choice == label
                          ? forge.goldDeep
                          : forge.surface2,
                      borderRadius:
                          BorderRadius.circular(ForgeShape.pillRadius),
                      border: Border.all(
                        color: _choice == label
                            ? forge.gold
                            : forge.strokeSoft,
                      ),
                    ),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 8),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Icon(icon,
                            size: 14,
                            color: _choice == label
                                ? Colors.white
                                : forge.textSub),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                          label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            fontWeight: FontWeight.w600,
                            color: _choice == label
                                ? Colors.white
                                : forge.text,
                          ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
          if (_choice != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(
              "Recorded privately. A person follows up if you asked for one.",
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.chip,
                color: forge.textSub,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// The dashed upload target.
class DottedDropZone extends StatelessWidget {
  const DottedDropZone({required this.onTap, super.key});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
      child: CustomPaint(
        painter: _DashedBorderPainter(color: forge.stroke),
        // A minimum height rather than a fixed one: at large accessibility
        // text sizes the caption wraps and the zone grows with it.
        child: Container(
          width: double.infinity,
          constraints: const BoxConstraints(minHeight: 88),
          padding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(Icons.upload_file, size: 21, color: forge.textSub),
              const SizedBox(height: 7),
              Text(
                "Drop a file to submit it for checking",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.caption,
                  color: forge.textSub,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashedBorderPainter extends CustomPainter {
  const _DashedBorderPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..color = color;

    final Path path = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          Offset.zero & size,
          const Radius.circular(ForgeShape.cardRadius),
        ),
      );

    // Walk the outline, drawing short segments with gaps between them.
    const double dash = 6;
    const double gap = 5;
    for (final PathMetric metric in path.computeMetrics()) {
      double distance = 0;
      while (distance < metric.length) {
        canvas.drawPath(
          metric.extractPath(distance, distance + dash),
          paint,
        );
        distance += dash + gap;
      }
    }
  }

  @override
  bool shouldRepaint(covariant _DashedBorderPainter old) => old.color != color;
}
