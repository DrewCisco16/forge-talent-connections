import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";

/// The five destinations in the app shell.
enum ForgeTab {
  home("Home", Icons.home_rounded),
  discover("Discover", Icons.explore_outlined),
  create("Create", Icons.add_circle_outline),
  projects("Projects", Icons.folder_outlined),
  me("Me", Icons.person_outline);

  const ForgeTab(this.label, this.icon);

  final String label;
  final IconData icon;
}

/// The bottom navigation bar. The active destination is gold.
class BottomNav extends StatelessWidget {
  const BottomNav({required this.current, required this.onSelected, super.key});

  final ForgeTab current;
  final ValueChanged<ForgeTab> onSelected;

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: ForgeColors.navyDeep,
        border: Border(top: BorderSide(color: forge.strokeSoft)),
      ),
      padding: const EdgeInsets.only(top: 8, bottom: 10),
      child: SafeArea(
        top: false,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: <Widget>[
            for (final ForgeTab tab in ForgeTab.values)
              Expanded(
                child: InkWell(
                  onTap: () => onSelected(tab),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Icon(
                        tab.icon,
                        size: 21,
                        color: tab == current ? forge.gold : forge.textSub,
                      ),
                      const SizedBox(height: 3),
                      Text(
                        tab.label,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          fontWeight:
                              tab == current ? FontWeight.w700 : FontWeight.w400,
                          color: tab == current ? forge.gold : forge.textSub,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
