import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// C5 Notifications.
///
/// A blocked export is reported here as plainly as a success is. Bad news is
/// never quietly dropped from the activity list.
class C5Notifications extends ConsumerWidget {
  const C5Notifications({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: AsyncView<List<AppNotification>>(
        value: ref.watch(notificationsProvider),
        pendingLabel: "Loading activity",
        builder: (List<AppNotification> items) {
          final List<AppNotification> today = items
              .where((AppNotification n) => n.isToday)
              .toList();
          final List<AppNotification> earlier = items
              .where((AppNotification n) => !n.isToday)
              .toList();

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              const SizedBox(height: 24),
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      "Activity",
                      style: TextStyle(
                        fontFamily: ForgeType.displayFamily,
                        fontSize: ForgeType.screenTitle,
                        fontWeight: FontWeight.bold,
                        color: forge.text,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    "Mark all read",
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.caption,
                      fontWeight: FontWeight.w600,
                      color: forge.gold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: ForgeSpacing.gapSection),
              if (today.isNotEmpty) ...<Widget>[
                const SectionLabel("Today"),
                const SizedBox(height: ForgeSpacing.gapCard),
                for (final AppNotification n in today)
                  _NotificationCard(notification: n),
              ],
              if (earlier.isNotEmpty) ...<Widget>[
                const SizedBox(height: ForgeSpacing.gapSection),
                const SectionLabel("Earlier"),
                const SizedBox(height: ForgeSpacing.gapCard),
                for (final AppNotification n in earlier)
                  _NotificationCard(notification: n),
              ],
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.notification});

  final AppNotification notification;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    final (IconData icon, Color accent) = switch (notification.kind) {
      NotificationKind.deliverableVerified => (Icons.check_circle, forge.green),
      NotificationKind.matchFound => (Icons.auto_awesome, forge.cyan),
      NotificationKind.message => (Icons.chat_bubble_outline, forge.textSub),
      NotificationKind.exportBlocked => (Icons.lock, forge.red),
      NotificationKind.milestoneApproved => (Icons.flag_outlined, forge.gold),
    };

    return Container(
      margin: const EdgeInsets.only(bottom: ForgeSpacing.gapCard),
      decoration: BoxDecoration(
        color: forge.surface,
        borderRadius: BorderRadius.circular(ForgeShape.cardRadius),
        border: Border.all(
          color: notification.unread ? forge.gold : forge.strokeSoft,
          width: notification.unread ? 1.4 : 1,
        ),
      ),
      padding: const EdgeInsets.all(ForgeSpacing.cardPad),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, size: 17, color: accent),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        notification.title,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.body,
                          fontWeight: FontWeight.w700,
                          color:
                              notification.kind ==
                                  NotificationKind.exportBlocked
                              ? forge.red
                              : forge.text,
                        ),
                      ),
                    ),
                    Text(
                      notification.when,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.chip,
                        color: forge.textSub,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  notification.body,
                  style: TextStyle(
                    fontFamily: ForgeType.bodyFamily,
                    fontSize: ForgeType.caption,
                    height: 1.35,
                    color: forge.textSub,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
