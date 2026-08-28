import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/app/device_frame.dart";

/// The width the child actually gets laid out at.
Future<double> _childWidth(WidgetTester tester, Size deviceSize) async {
  final GlobalKey probe = GlobalKey();
  tester.view.physicalSize = deviceSize;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(size: deviceSize),
        child: ForgeDeviceFrame(
          child: SizedBox.expand(key: probe),
        ),
      ),
    ),
  );
  await tester.pump();
  return tester.getSize(find.byKey(probe)).width;
}

void main() {
  group("ForgeDeviceFrame", () {
    testWidgets("a phone gets the full width, untouched",
        (WidgetTester tester) async {
      expect(await _childWidth(tester, const Size(440, 956)), 440);
    });

    testWidgets("the narrowest supported phone is untouched",
        (WidgetTester tester) async {
      expect(await _childWidth(tester, const Size(375, 667)), 375);
    });

    testWidgets("an iPad in portrait is held to the content column",
        (WidgetTester tester) async {
      // 834 wide would stretch a 390-wide design across the whole glass.
      expect(
        await _childWidth(tester, const Size(834, 1194)),
        ForgeDeviceFrame.maxContentWidth,
      );
    });

    testWidgets("an iPad in landscape is held to the same column",
        (WidgetTester tester) async {
      expect(
        await _childWidth(tester, const Size(1194, 834)),
        ForgeDeviceFrame.maxContentWidth,
      );
    });

    testWidgets("the column is centred, not pinned to one edge",
        (WidgetTester tester) async {
      final GlobalKey probe = GlobalKey();
      const Size ipad = Size(834, 1194);
      tester.view.physicalSize = ipad;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(size: ipad),
            child: ForgeDeviceFrame(child: SizedBox.expand(key: probe)),
          ),
        ),
      );
      await tester.pump();

      final double left = tester.getTopLeft(find.byKey(probe)).dx;
      final double right = tester.getTopRight(find.byKey(probe)).dx;
      expect(left, closeTo((ipad.width - ForgeDeviceFrame.maxContentWidth) / 2, 0.5));
      expect(ipad.width - right, closeTo(left, 0.5));
    });

    testWidgets("inside the column the app sees the narrow width",
        (WidgetTester tester) async {
      // Screens read MediaQuery to lay themselves out. If they still saw the
      // iPad's full width inside a 480-wide column, they would overflow it.
      late double seenWidth;
      const Size ipad = Size(834, 1194);
      tester.view.physicalSize = ipad;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(size: ipad),
            child: ForgeDeviceFrame(
              child: Builder(
                builder: (BuildContext context) {
                  seenWidth = MediaQuery.sizeOf(context).width;
                  return const SizedBox.expand();
                },
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      expect(seenWidth, ForgeDeviceFrame.maxContentWidth);
    });
  });
}
