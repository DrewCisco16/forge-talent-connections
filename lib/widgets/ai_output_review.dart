import "package:flutter/material.dart";

import "../theme/forge_theme.dart";
import "../theme/tokens.dart";
import "section_label.dart";

/// A short review a person runs before acting on anything an AI produced.
///
/// Every AI surface in the product (a match suggestion, an assistant answer,
/// the Talent Signature) carries this card so the critical check travels
/// with the output instead of living in a help page. The eight lines are the
/// product's own answers to the questions a careful reader asks of any AI
/// output: is it accurate, does it match my intent, what is missing, is it
/// relevant, does it rest on one source, is the tone right, how does it get
/// better, and is it safe to act on. The last line is the two-human rule and
/// never changes.
class AiOutputReview extends StatelessWidget {
  const AiOutputReview({required this.subject, super.key});

  /// What is being reviewed, in the sentence position "before you use
  /// [subject]": "this suggestion", "this answer", "this signature".
  final String subject;

  static const List<(String, String, String)> checks =
      <(String, String, String)>[
        ("A", "Accurate", "Built only from verified records, never claims."),
        ("I", "Intent", "Answers what you asked, not what is easiest."),
        ("C", "Complete", "Says plainly what it does not know."),
        ("R", "Relevant", "Tied to this project, not a generic profile."),
        ("I", "Independent", "Names every source. Never one unnamed source."),
        ("T", "Tone", "Plain language. No promises, no pressure."),
        ("Q", "Question It", "Ask the reviewer anything it left out."),
        ("U", "Use", "A suggestion only. Two humans decide."),
      ];

  @override
  Widget build(BuildContext context) {
    final ForgeTheme forge = ForgeTheme.of(context);
    return ForgeCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Text(
            "Before You Use This",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.cardTitle,
              fontWeight: FontWeight.w700,
              color: forge.gold,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            "Eight checks a person runs before acting on $subject.",
            style: TextStyle(
              fontFamily: ForgeType.bodyFamily,
              fontSize: ForgeType.caption,
              height: 1.4,
              color: forge.textSub,
            ),
          ),
          const SizedBox(height: 10),
          for (final (String letter, String label, String line) in checks)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  ExcludeSemantics(
                    child: Container(
                      width: 22,
                      height: 22,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: forge.gold.withValues(alpha: 0.16),
                        border: Border.all(
                          color: forge.gold.withValues(alpha: 0.55),
                        ),
                      ),
                      child: Text(
                        letter,
                        textScaler: TextScaler.noScaling,
                        style: TextStyle(
                          fontFamily: ForgeType.bodyFamily,
                          fontSize: ForgeType.caption,
                          fontWeight: FontWeight.w700,
                          color: forge.gold,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text.rich(
                      TextSpan(
                        children: <InlineSpan>[
                          TextSpan(
                            text: "$label. ",
                            style: TextStyle(
                              fontWeight: FontWeight.w700,
                              color: forge.text,
                            ),
                          ),
                          TextSpan(text: line),
                        ],
                      ),
                      style: TextStyle(
                        fontFamily: ForgeType.bodyFamily,
                        fontSize: ForgeType.body,
                        height: 1.35,
                        color: forge.textSub,
                      ),
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
