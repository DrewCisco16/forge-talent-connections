import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/banner_note.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/seal_card.dart";
import "../../widgets/section_label.dart";
import "../../widgets/status_chip.dart";

/// D1 Integrity certificate and export.
///
/// The denial path is the point of this screen. A file that did not pass its
/// check is shown as locked, the reason is stated, and the export action is
/// disabled rather than allowed to look like it might work.
class D1ExportCertificate extends ConsumerWidget {
  const D1ExportCertificate({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: AsyncView<List<ExportItem>>(
        value: ref.watch(exportQueueProvider),
        pendingLabel: "Checking files",
        builder: (List<ExportItem> queue) {
          final List<ExportItem> blocked = queue
              .where((ExportItem e) => e.status.blocksRelease)
              .toList();
          final bool anyBlocked = blocked.isNotEmpty;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              const SizedBox(height: 24),
              Text(
                anyBlocked ? "Export blocked" : "Export ready",
                style: TextStyle(
                  fontFamily: ForgeType.displayFamily,
                  fontSize: ForgeType.screenTitle,
                  fontWeight: FontWeight.bold,
                  color: anyBlocked ? forge.red : forge.text,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                "Only verified work leaves the building.",
                style: TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.body,
                  color: forge.textSub,
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapSection),
              AsyncView<IntegrityCertificate>(
                value: ref.watch(certificateProvider),
                pendingLabel: "Loading certificate",
                builder: (IntegrityCertificate cert) => SealCard(
                  title: "Integrity Certificate",
                  text: cert.filename,
                  rows: <MapEntry<String, String>>[
                    MapEntry(
                      "Status",
                      switch (cert.status) {
                        VerificationStatus.verified => "VERIFIED",
                        VerificationStatus.pending => "PENDING",
                        VerificationStatus.unverified => "UNVERIFIED",
                        VerificationStatus.failed => "FAILED",
                        VerificationStatus.locked => "LOCKED",
                      },
                    ),
                    MapEntry("Checked", cert.checkedOn),
                    MapEntry("Fingerprint", cert.fingerprint),
                    MapEntry(
                      "Delivered exactly as created",
                      cert.deliveredAsCreated ? "Yes" : "No",
                    ),
                  ],
                ),
              ),
              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Files in this export"),
              const SizedBox(height: ForgeSpacing.gapCard),
              for (final ExportItem e in queue)
                Container(
                  margin: const EdgeInsets.only(bottom: ForgeSpacing.gapCard),
                  decoration: BoxDecoration(
                    color: forge.surface,
                    borderRadius:
                        BorderRadius.circular(ForgeShape.cardRadius),
                    border: Border.all(
                      color: e.status.blocksRelease
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
                              e.filename,
                              style: TextStyle(
                                fontFamily: ForgeType.bodyFamily,
                                fontSize: ForgeType.body,
                                fontWeight: FontWeight.w600,
                                color: forge.text,
                              ),
                            ),
                          ),
                          StatusChip(status: e.status, dense: true),
                        ],
                      ),
                      if (e.reason != null) ...<Widget>[
                        const SizedBox(height: 6),
                        Text(
                          e.reason!,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            color: forge.red,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              if (anyBlocked) ...<Widget>[
                const SizedBox(height: ForgeSpacing.gapCard),
                // Required copy. Ships verbatim.
                BannerNote(
                  tone: BannerTone.denial,
                  text: blocked.length == 1
                      ? "1 file failed its check and stays locked. If it does not match, it does not go out."
                      : "${blocked.length} files failed their check and stay locked. If it does not match, it does not go out.",
                ),
              ],
              const SizedBox(height: ForgeSpacing.gapSection),
              const SectionLabel("Share to"),
              const SizedBox(height: ForgeSpacing.gapCard),
              Row(
                children: <Widget>[
                  for (final (IconData icon, String label) in <(IconData, String)>[
                    (Icons.work_outline, "LinkedIn"),
                    (Icons.link, "Link"),
                    (Icons.qr_code, "QR"),
                    (Icons.picture_as_pdf_outlined, "PDF"),
                  ])
                    Padding(
                      padding: const EdgeInsets.only(right: 14),
                      child: Column(
                        children: <Widget>[
                          Opacity(
                            opacity: anyBlocked ? 0.4 : 1,
                            child: Container(
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(color: forge.strokeSoft),
                              ),
                              padding: const EdgeInsets.all(12),
                              child:
                                  Icon(icon, size: 18, color: forge.text),
                            ),
                          ),
                          const SizedBox(height: 5),
                          Text(
                            label,
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.chip,
                              color: forge.textSub,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
              const SizedBox(height: ForgeSpacing.gapSection),
              // A blocked export offers no action that could appear to succeed.
              GoldButton(
                label: anyBlocked
                    ? "Export blocked"
                    : "Export Verified Work",
                onPressed: anyBlocked ? null : () {},
              ),
              if (anyBlocked) ...<Widget>[
                const SizedBox(height: 8),
                Text(
                  "Resolve the locked file before anything can be exported.",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    color: forge.textSub,
                  ),
                ),
              ],
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }
}
