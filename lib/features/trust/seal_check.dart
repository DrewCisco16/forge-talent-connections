import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// Seal Check — the page a check link opens for someone outside the app.
///
/// Selective disclosure is the whole design: the visitor learns whether the
/// seal is genuine and unaltered, and nothing else. No documents, no
/// profile, no history. The verdict comes from the backend; an unknown or
/// failed check renders as exactly that, never as an optimistic maybe.
class SealCheck extends ConsumerWidget {
  const SealCheck({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          InkWell(
            onTap: () => context.go("/export"),
            child: Row(
              children: <Widget>[
                Icon(Icons.arrow_back, size: 17, color: forge.gold),
                const SizedBox(width: 8),
                Text(
                  "Back",
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.body,
                    fontWeight: FontWeight.w600,
                    color: forge.gold,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const Align(alignment: Alignment.centerRight, child: DemoBadge()),
          const SizedBox(height: 8),
          Text(
            "Seal Check",
            style: TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: ForgeType.screenTitle,
              fontWeight: FontWeight.bold,
              color: forge.text,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            "What anyone with the link sees — and all they see.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<IntegrityCertificate>(
            value: ref.watch(certificateProvider),
            pendingLabel: "Checking the seal",
            builder: (IntegrityCertificate cert) {
              final bool valid = cert.status == VerificationStatus.verified;
              final bool pending = cert.status == VerificationStatus.pending;
              final Color verdictColor =
                  valid ? forge.green : (pending ? forge.gold : forge.red);
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  ForgeCard(
                    borderColor: verdictColor,
                    child: Column(
                      children: <Widget>[
                        Icon(
                          valid
                              ? Icons.verified
                              : pending
                                  ? Icons.hourglass_top
                                  : Icons.gpp_bad_outlined,
                          size: 44,
                          color: verdictColor,
                        ),
                        const SizedBox(height: 10),
                        Text(
                          valid
                              ? "SEAL VALID"
                              : pending
                                  ? "CHECK PENDING"
                                  : "NOT VALID",
                          style: TextStyle(
                            fontFamily: ForgeType.displayFamily,
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 2,
                            color: verdictColor,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          valid
                              ? "This record is genuine and has not been "
                                  "altered since it was sealed."
                              : pending
                                  ? "The check has not finished. Nothing is "
                                      "confirmed yet."
                                  : "This seal could not be confirmed. Treat "
                                      "the record as unverified.",
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.body,
                            height: 1.4,
                            color: forge.text,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Container(
                          decoration: BoxDecoration(
                            color: forge.surface2,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 8),
                          child: Column(
                            children: <Widget>[
                              _KV("Sealed item", cert.filename),
                              _KV("Checked", cert.checkedOn),
                              _KV("Fingerprint", cert.fingerprint),
                              const _KV("Sealed by",
                                  "FORGE Talent Connections verification"),
                              const _KV("Valid",
                                  "Until the record changes"),
                              const _KV("Corrections",
                                  "Human review on request"),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: ForgeSpacing.gapSection),
                  ForgeCard(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Icon(Icons.visibility_off_outlined,
                            size: 17, color: forge.textSub),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            "Documents are never shown here. A check link "
                            "proves the seal — it discloses nothing else.",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              height: 1.4,
                              color: forge.textSub,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Text(
            "Checked by FORGE Talent Connections",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _KV extends StatelessWidget {
  // ignore: unused_element_parameter
  const _KV(this.k, this.v, {super.key});

  final String k;
  final String v;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              k,
              style: TextStyle(
                fontFamily: ForgeType.bodyFamily,
                fontSize: ForgeType.caption,
                color: forge.textSub,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              v,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
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
    );
  }
}
