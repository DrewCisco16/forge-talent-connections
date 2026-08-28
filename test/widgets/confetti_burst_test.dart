import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/widgets/confetti_burst.dart";

/// The celebration burst is one-shot, honest, and optional.
///
/// It paints only while playing, ends on its own, and paints nothing at all
/// under reduced motion — the signed state, not the animation, is the record.
void main() {
  Finder burstPaint() => find.descendant(
        of: find.byType(ConfettiBurst),
        matching: find.byType(CustomPaint),
      );

  testWidgets("plays once on the rising edge and ends by itself",
      (WidgetTester tester) async {
    bool play = false;
    late StateSetter setPlay;
    await tester.pumpWidget(
      MaterialApp(
        home: StatefulBuilder(
          builder: (BuildContext context, StateSetter setState) {
            setPlay = setState;
            return SizedBox(
              width: 400,
              height: 600,
              child: ConfettiBurst(
                play: play,
                colors: const <Color>[Colors.amber, Colors.purple],
              ),
            );
          },
        ),
      ),
    );

    expect(burstPaint(), findsNothing);

    setPlay(() => play = true);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));
    expect(burstPaint(), findsWidgets);

    await tester.pump(const Duration(seconds: 2));
    expect(burstPaint(), findsNothing);
  });

  testWidgets("reduced motion: nothing is painted",
      (WidgetTester tester) async {
    bool play = false;
    late StateSetter setPlay;
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: StatefulBuilder(
            builder: (BuildContext context, StateSetter setState) {
              setPlay = setState;
              return SizedBox(
                width: 400,
                height: 600,
                child: ConfettiBurst(
                  play: play,
                  colors: const <Color>[Colors.amber],
                ),
              );
            },
          ),
        ),
      ),
    );

    setPlay(() => play = true);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));
    expect(burstPaint(), findsNothing);
  });
}
