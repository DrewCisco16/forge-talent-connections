import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/demo_note.dart";
import "../../widgets/section_label.dart";
import "../../widgets/social_action.dart";
import "../../widgets/status_chip.dart";

/// Talent Stories: the vertical browser of verified video introductions.
///
/// One Story fills the screen; a swipe up brings the next. The demo is
/// honest about its own limits: the people are samples and no footage is
/// invented for them, so each page renders a poster frame with the Story's
/// caption and says so on screen. In production a Story is a real upload
/// carrying the same verification standard as everything else.
class TalentStories extends ConsumerStatefulWidget {
  const TalentStories({super.key});

  @override
  ConsumerState<TalentStories> createState() => _TalentStoriesState();
}

class _TalentStoriesState extends ConsumerState<TalentStories> {
  final PageController _pager = PageController();
  int _page = 0;

  @override
  void dispose() {
    _pager.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Scaffold(
      backgroundColor: ForgeColors.navyDeep,
      body: SafeArea(
        child: AsyncView<List<TalentStory>>(
          value: ref.watch(talentStoriesProvider),
          pendingLabel: "Loading Talent Stories",
          builder: (List<TalentStory> stories) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 6, 14, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Semantics(
                          button: true,
                          label: "Back to the feed",
                          child: IconButton(
                            onPressed: () => context.go("/feed"),
                            icon: Icon(
                              Icons.arrow_back,
                              size: 22,
                              color: forge.text,
                            ),
                          ),
                        ),
                        Expanded(
                          child: Text(
                            "Talent Stories",
                            style: TextStyle(
                              fontFamily: ForgeType.displayFamily,
                              fontSize: ForgeType.cardTitle,
                              fontWeight: FontWeight.bold,
                              color: forge.text,
                            ),
                          ),
                        ),
                        Text(
                          "${_page + 1} of ${stories.length}",
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.caption,
                            color: forge.textSub,
                          ),
                        ),
                      ],
                    ),
                    // The badge sits on its own line so large accessibility
                    // text reflows instead of crowding the title.
                    const Align(
                      alignment: Alignment.centerRight,
                      child: DemoBadge(),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: PageView.builder(
                  controller: _pager,
                  scrollDirection: Axis.vertical,
                  itemCount: stories.length,
                  onPageChanged: (int i) => setState(() => _page = i),
                  itemBuilder: (BuildContext context, int i) =>
                      _StoryPage(story: stories[i]),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
                child: Text(
                  "Swipe up for the next Story. These are labelled samples: "
                  "no footage is invented for sample people. Within the "
                  "year, Talent Stories becomes a full feature with real "
                  "uploads under the same verification standard.",
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
      ),
    );
  }
}

/// One full-height Story page: author, poster frame, caption, vouch rail.
class _StoryPage extends StatelessWidget {
  const _StoryPage({required this.story});

  final TalentStory story;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: 8),
          Row(
            children: <Widget>[
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(colors: forge.goldGradient),
                ),
                padding: const EdgeInsets.all(2),
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    image: DecorationImage(
                      image: AssetImage(story.authorAvatar),
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Flexible(
                          child: Text(
                            story.authorName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.body,
                              fontWeight: FontWeight.w700,
                              color: forge.text,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        StatusChip(status: story.authorStatus, dense: true),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      story.headline,
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
          Expanded(
            child: Stack(
              children: <Widget>[
                Center(
                  child: Semantics(
                    button: true,
                    label: "Play Story, sample entry",
                    child: InkWell(
                      customBorder: const CircleBorder(),
                      onTap: () => demoNote(
                        context,
                        "Demo Story: a labelled sample. No footage is "
                        "invented for sample people; your own Story records "
                        "in the pitch studio.",
                      ),
                      child: Icon(
                        Icons.play_circle_outline,
                        size: 60,
                        color: forge.textSub.withValues(alpha: 0.5),
                      ),
                    ),
                  ),
                ),
                Positioned(
                  right: 0,
                  bottom: 90,
                  child: Column(
                    children: <Widget>[
                      VibeButton(
                        label: "Vouch",
                        onPressed: () => context.go("/vouch"),
                      ),
                      const SizedBox(height: 14),
                      Icon(Icons.favorite_border, size: 22, color: forge.text),
                      Text(
                        "${story.vouchCount}",
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          color: forge.textSub,
                        ),
                      ),
                    ],
                  ),
                ),
                Positioned(
                  left: 0,
                  right: 70,
                  bottom: 44,
                  child: Container(
                    decoration: BoxDecoration(
                      color: ForgeColors.navyDeep.withValues(alpha: 0.75),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    padding: const EdgeInsets.all(9),
                    child: Text(
                      story.caption,
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.caption,
                        height: 1.35,
                        color: forge.text,
                      ),
                    ),
                  ),
                ),
                Positioned(
                  left: 0,
                  bottom: 12,
                  child: Row(
                    children: <Widget>[
                      for (final String tag in story.tags)
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: Text(
                            tag,
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.caption,
                              fontWeight: FontWeight.w600,
                              color: forge.cyan,
                            ),
                          ),
                        ),
                    ],
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
