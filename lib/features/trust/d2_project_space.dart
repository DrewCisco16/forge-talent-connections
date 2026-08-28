import "dart:ui" show PathMetric;

import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
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
              DottedDropZone(onTap: () {}),
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
        child: SizedBox(
          height: 88,
          width: double.infinity,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(Icons.upload_file, size: 21, color: forge.textSub),
              const SizedBox(height: 7),
              Text(
                "Drop a file to submit it for checking",
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
