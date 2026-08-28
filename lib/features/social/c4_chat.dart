import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/status_chip.dart";

/// C4 Chat with verified file share.
class C4Chat extends ConsumerWidget {
  const C4Chat({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: AsyncView<ChatThread>(
        value: ref.watch(chatThreadProvider),
        pendingLabel: "Loading conversation",
        builder: (ChatThread thread) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            const SizedBox(height: ForgeSpacing.gapSection),
            Row(
              children: <Widget>[
                InkWell(
                  onTap: () => context.go("/feed"),
                  child: Icon(Icons.arrow_back, size: 19, color: forge.text),
                ),
                const SizedBox(width: 12),
                // Expanded so a long name or presence line truncates at
                // large text sizes instead of pushing past the edge.
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        thread.withName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.cardTitle,
                          fontWeight: FontWeight.w700,
                          color: forge.text,
                        ),
                      ),
                      Text(
                        thread.presence,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          color: forge.green,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            for (final ChatMessage m in thread.messages)
              Align(
                alignment:
                    m.fromMe ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 260),
                  margin: const EdgeInsets.only(bottom: 10),
                  decoration: BoxDecoration(
                    color: m.fromMe ? forge.goldDeep : forge.surface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: m.fromMe ? forge.goldDeep : forge.strokeSoft,
                    ),
                  ),
                  padding: const EdgeInsets.all(12),
                  child: m.attachmentName != null
                      ? _FileShare(
                          name: m.attachmentName!,
                          status: m.attachmentStatus!,
                        )
                      : Text(
                          m.text,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.body,
                            height: 1.3,
                            color: m.fromMe ? Colors.white : forge.text,
                          ),
                        ),
                ),
              ),
            Align(
              alignment: Alignment.centerLeft,
              child: Container(
                margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(
                  color: forge.surface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: forge.strokeSoft),
                ),
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    for (int i = 0; i < 3; i++)
                      Padding(
                        padding: const EdgeInsets.only(right: 4),
                        child: Icon(Icons.circle,
                            size: 5, color: forge.textSub),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: ForgeSpacing.gapSection),
            Row(
              children: <Widget>[
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: forge.surface2,
                      borderRadius:
                          BorderRadius.circular(ForgeShape.pillRadius),
                      border: Border.all(color: forge.strokeSoft),
                    ),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 11),
                    child: Text(
                      "Message",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.body,
                        color: forge.textSub,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(colors: forge.goldGradient),
                  ),
                  padding: const EdgeInsets.all(11),
                  child: const Icon(Icons.send, size: 17, color: Colors.white),
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

class _FileShare extends StatelessWidget {
  const _FileShare({required this.name, required this.status});

  final String name;
  final VerificationStatus status;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            const Icon(Icons.insert_drive_file_outlined,
                size: 17, color: Colors.white),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                name,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontFamily: ForgeType.bodyFamily,
                  fontSize: ForgeType.body,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        StatusChip(status: status, dense: true),
        if (status.blocksRelease) ...<Widget>[
          const SizedBox(height: 6),
          Text(
            "This file did not pass its check. It cannot be forwarded.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.chip,
              color: forge.text,
            ),
          ),
        ],
      ],
    );
  }
}
