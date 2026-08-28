import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../mock/fixtures.dart";
import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/phone_scaffold.dart";

/// A3 Choose your avatar.
class A3ChooseAvatar extends ConsumerStatefulWidget {
  const A3ChooseAvatar({super.key});

  @override
  ConsumerState<A3ChooseAvatar> createState() => _A3ChooseAvatarState();
}

class _A3ChooseAvatarState extends ConsumerState<A3ChooseAvatar> {
  // Opens on the persona's own avatar rather than the first cell, so the
  // screen reflects who the user actually is.
  int _selected = kDrewAvatarIndex;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: 24),
          Text(
            "Choose Your Avatar",
            style: TextStyle(
              fontFamily: ForgeType.displayFamily,
              fontSize: ForgeType.screenTitle,
              fontWeight: FontWeight.bold,
              color: forge.text,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            "Pick the hero that represents you",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.body,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 4),
          AsyncView<List<AvatarOption>>(
            value: ref.watch(avatarsProvider),
            pendingLabel: "Loading avatars",
            builder: (List<AvatarOption> avatars) => GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: avatars.length,
              gridDelegate:
                  const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 4,
                mainAxisSpacing: 14,
                crossAxisSpacing: 14,
              ),
              itemBuilder: (BuildContext context, int i) => _AvatarCell(
                asset: avatars[i].asset,
                selected: i == _selected,
                onTap: () => setState(() => _selected = i),
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 6),
          Center(
            child: Container(
              width: 140,
              height: 140,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(colors: forge.goldGradient),
              ),
              padding: const EdgeInsets.all(5),
              child: Container(
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  image: DecorationImage(
                    image: AssetImage(kAvatarPreview),
                    fit: BoxFit.cover,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection + 6),
          Row(
            children: <Widget>[
              Expanded(
                child: OutlineGoldButton(
                  label: "Cancel",
                  onPressed: () => context.go("/create-profile"),
                ),
              ),
              const SizedBox(width: ForgeSpacing.gapCard),
              Expanded(
                child: GoldButton(
                  label: "Use This Avatar",
                  onPressed: () => context.go("/veteran-verification"),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _AvatarCell extends StatelessWidget {
  const _AvatarCell({
    required this.asset,
    required this.selected,
    required this.onTap,
  });

  final String asset;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return InkWell(
      onTap: onTap,
      customBorder: const CircleBorder(),
      child: Stack(
        children: <Widget>[
          Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: selected
                  ? LinearGradient(colors: forge.goldGradient)
                  : null,
              border: selected ? null : Border.all(color: forge.strokeSoft),
            ),
            padding: EdgeInsets.all(selected ? 4 : 1),
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                image: DecorationImage(
                  image: AssetImage(asset),
                  fit: BoxFit.cover,
                ),
              ),
            ),
          ),
          if (selected)
            Positioned(
              right: 0,
              bottom: 0,
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(colors: forge.goldGradient),
                  border: Border.all(color: ForgeColors.navyDeep, width: 1.5),
                ),
                padding: const EdgeInsets.all(3),
                child: const Icon(Icons.check, size: 11, color: Colors.white),
              ),
            ),
        ],
      ),
    );
  }
}
