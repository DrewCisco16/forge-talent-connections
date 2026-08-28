import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/feed_card.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";
import "../../widgets/social_action.dart";

/// C1 Social feed.
class C1Feed extends ConsumerWidget {
  const C1Feed({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: <Widget>[
              // The brand is always the whole name: wordmark plus descriptor.
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    GoldGradientText(
                      "FORGE",
                      style: const TextStyle(
                        fontFamily: ForgeType.displayFamily,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 2,
                      ),
                    ),
                    Text(
                      "TALENT CONNECTIONS",
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.chip,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 2.4,
                        color: forge.textSub,
                      ),
                    ),
                  ],
                ),
              ),
              Semantics(
                button: true,
                label: "Notifications",
                child: InkWell(
                  onTap: () => context.go("/notifications"),
                  child: Container(
                    width: 44,
                    height: 44,
                    alignment: Alignment.center,
                    child: Icon(Icons.notifications_none,
                        size: 21, color: forge.gold),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<List<Story>>(
            value: ref.watch(storiesProvider),
            pendingLabel: "Loading stories",
            builder: (List<Story> stories) => SizedBox(
              // Ring (62) + gap + one label line; the label line grows with
              // the accessibility text setting so names never clip.
              height: 74 +
                  MediaQuery.textScalerOf(context).scale(ForgeType.caption) *
                      1.6,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: stories.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (BuildContext context, int i) => InkWell(
                  onTap: () => context.go("/video-pitch"),
                  child: StoryRing(
                    label: stories[i].name,
                    image: AssetImage(stories[i].avatar),
                    isSelf: stories[i].isSelf,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          ForgeCard(
            borderColor: forge.violet.withValues(alpha: 0.5),
            background: forge.violet.withValues(alpha: 0.09),
            child: Row(
              children: <Widget>[
                Icon(Icons.local_fire_department,
                    size: 22, color: forge.violet),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        "5-week build streak",
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.cardTitle,
                          fontWeight: FontWeight.w700,
                          color: forge.text,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        "Ship one verified deliverable this week to keep it",
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          color: forge.textSub,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          AsyncView<List<FeedPost>>(
            value: ref.watch(feedProvider),
            pendingLabel: "Loading feed",
            builder: (List<FeedPost> posts) => Column(
              children: <Widget>[
                for (final FeedPost p in posts) ...<Widget>[
                  FeedCard(
                    name: p.authorName,
                    status: p.authorStatus,
                    avatar: AssetImage(p.authorAvatar),
                    event: p.event,
                    body: p.body,
                    vouchCount: p.vouchCount,
                    action: VibeButton(
                      label: "Vouch",
                      onPressed: () => context.go("/vouch"),
                    ),
                    onMessage: () => context.go("/chat"),
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
