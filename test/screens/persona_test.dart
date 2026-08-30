import "package:flutter_test/flutter_test.dart";
import "package:forge_talent_connections/mock/fixtures.dart";
import "package:forge_talent_connections/mock/mock_repository.dart";
import "package:forge_talent_connections/models/models.dart";

/// The demo persona's identity.
///
/// Drew Cisco stands in for the product owner, so the avatar must be male.
/// Getting this wrong is not a cosmetic bug: it puts a likeness on screen
/// representing a real person who did not consent to it. These tests pin it.
void main() {
  /// Avatars 01 through 09 depict women; 10 through 16 depict men.
  const int firstMaleIndex = 9;

  group("demo persona", () {
    test("the persona avatar is drawn from the male set", () {
      final int index = kAvatars.indexWhere(
        (AvatarOption a) => a.asset == kDrewAvatar,
      );
      expect(
        index,
        greaterThanOrEqualTo(firstMaleIndex),
        reason: "kDrewAvatar must be one of heroes 10-16",
      );
      expect(
        index,
        kDrewAvatarIndex,
        reason: "kDrewAvatarIndex must point at kDrewAvatar",
      );
    });

    test("the profile served to the app uses that avatar", () async {
      for (final DemoScenario scenario in DemoScenario.values) {
        final UserProfile profile = await MockForgeRepository(scenario)
            .loadProfile();
        expect(
          profile.avatarAsset,
          kDrewAvatar,
          reason: "the persona avatar must not vary by scenario",
        );
      }
    });

    test("the persona's own story ring uses that avatar", () async {
      final List<Story> stories = await const MockForgeRepository(
        DemoScenario.verified,
      ).loadStories();
      final Story self = stories.firstWhere((Story s) => s.isSelf);
      expect(self.avatar, kDrewAvatar);
    });

    test("no two people in the cast share a face", () async {
      const MockForgeRepository repo = MockForgeRepository(
        DemoScenario.verified,
      );
      final List<Story> stories = await repo.loadStories();
      final List<String> faces = stories.map((Story s) => s.avatar).toList();
      expect(
        faces.toSet().length,
        faces.length,
        reason: "two cast members are using the same avatar",
      );
    });
  });
}
