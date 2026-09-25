import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../mock/providers.dart";
import "../../models/models.dart";
import "../../theme/forge_theme.dart";
import "../../theme/tokens.dart";
import "../../widgets/async_view.dart";
import "../../widgets/demo_note.dart";
import "../../widgets/field_box.dart";
import "../../widgets/gold_button.dart";
import "../../widgets/hero_band.dart";
import "../../widgets/phone_scaffold.dart";
import "../../widgets/section_label.dart";

/// The AI Assistant: help, answers, and premium scholarly research.
///
/// The demo shows a scripted sample conversation and says so. In production
/// the assistant runs on Google Cloud Vertex AI behind the product backend;
/// it can explain, draft, and research, and it never writes to a record:
/// every change still passes the integrity check and the two-human standard.
class AiAssistant extends ConsumerWidget {
  const AiAssistant({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ForgeTheme forge = ForgeTheme.of(context);

    return PhoneScaffold(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: ForgeSpacing.gapSection),
          const Align(alignment: Alignment.centerRight, child: DemoBadge()),
          const SizedBox(height: 8),
          const HeroBand(
            title: "AI Assistant",
            subtitle: "Help, answers, and research on demand",
          ),
          const SizedBox(height: ForgeSpacing.gapCard),
          // What it can do, in three chips.
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              for (final (String label, bool premium) in <(String, bool)>[
                ("Answers about the product", false),
                ("Drafting help", false),
                ("Scholarly research · Premium", true),
              ])
                Container(
                  decoration: BoxDecoration(
                    color: (premium ? forge.gold : forge.violet).withValues(
                      alpha: 0.12,
                    ),
                    border: Border.all(
                      color: (premium ? forge.gold : forge.violet).withValues(
                        alpha: 0.55,
                      ),
                    ),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 5,
                  ),
                  child: Text(
                    label,
                    style: TextStyle(
                      fontFamily: ForgeType.bodyFamily,
                      fontSize: ForgeType.chip,
                      fontWeight: FontWeight.w700,
                      color: premium ? forge.gold : forge.violet,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          const SectionLabel("Sample conversation"),
          const SizedBox(height: 6),
          AsyncView<List<AssistantExchange>>(
            value: ref.watch(assistantTranscriptProvider),
            pendingLabel: "Loading the sample conversation",
            builder: (List<AssistantExchange> transcript) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                for (final AssistantExchange e in transcript) ...<Widget>[
                  Align(
                    alignment: Alignment.centerRight,
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 300),
                      decoration: BoxDecoration(
                        color: forge.gold.withValues(alpha: 0.14),
                        border: Border.all(
                          color: forge.gold.withValues(alpha: 0.45),
                        ),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 9,
                      ),
                      child: Text(
                        e.question,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.body,
                          height: 1.35,
                          color: forge.text,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  ForgeCard(
                    borderColor: e.premium
                        ? forge.gold.withValues(alpha: 0.55)
                        : null,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        if (e.premium) ...<Widget>[
                          Text(
                            "PREMIUM · SCHOLARLY RESEARCH",
                            style: TextStyle(
                              fontFamily: ForgeType.bodyFamily,
                              fontSize: ForgeType.chip,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.6,
                              color: forge.gold,
                            ),
                          ),
                          const SizedBox(height: 6),
                        ],
                        Text(
                          e.answer,
                          style: TextStyle(
                            fontFamily: ForgeType.bodyFamily,
                            fontSize: ForgeType.body,
                            height: 1.4,
                            color: forge.text,
                          ),
                        ),
                        for (final String r in e.sampleResults) ...<Widget>[
                          const SizedBox(height: 8),
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Icon(
                                Icons.menu_book_outlined,
                                size: 14,
                                color: forge.gold,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  r,
                                  style: TextStyle(
                                    fontFamily: ForgeType.bodyFamily,
                                    fontSize: ForgeType.caption,
                                    height: 1.35,
                                    color: forge.textSub,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: ForgeSpacing.gapCard),
                ],
              ],
            ),
          ),
          const SizedBox(height: 4),
          const FieldBox(label: "Ask anything", hint: "Type your question"),
          const SizedBox(height: ForgeSpacing.gapCard),
          GoldButton(
            label: "Ask the Assistant",
            onPressed: () => demoNote(
              context,
              "Demo assistant: this conversation is a scripted sample. The "
              "live assistant arrives with the backend.",
            ),
          ),
          const SizedBox(height: ForgeSpacing.gapSection),
          Text(
            "In production the assistant runs on Google Cloud Vertex AI "
            "behind the product backend, with usage limits and a spending "
            "cap. Research answers are found in real scholarly registries "
            "first; the assistant summarises only records that exist. It "
            "never writes to your record: every change still passes the "
            "integrity check, and no answer replaces the two humans behind "
            "a vouch. In this demo, replies are scripted samples.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.4,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
