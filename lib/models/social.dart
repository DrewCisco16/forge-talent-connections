import "verification_status.dart";

/// A pitch story ring in the feed.
class Story {
  const Story({
    required this.id,
    required this.name,
    required this.avatar,
    this.isSelf = false,
  });

  final String id;
  final String name;
  final String avatar;
  final bool isSelf;
}

/// An entry in the social feed.
class FeedPost {
  const FeedPost({
    required this.id,
    required this.authorName,
    required this.authorAvatar,
    required this.authorStatus,
    required this.event,
    required this.body,
    required this.vouchCount,
  });

  final String id;
  final String authorName;
  final String authorAvatar;
  final VerificationStatus authorStatus;

  /// The event line, for instance "shipped a verified deliverable".
  final String event;
  final String body;
  final int vouchCount;
}

/// One Talent Story: a short verified video introduction in the vertical
/// Story browser.
///
/// Demo entries are sample people, and no footage is invented for them: the
/// browser renders honest poster frames and says so. In production a Story
/// is a real upload that carries the same verification standard as
/// everything else - the badge on the author is earned, never decorative.
class TalentStory {
  const TalentStory({
    required this.id,
    required this.authorName,
    required this.authorAvatar,
    required this.authorStatus,
    required this.headline,
    required this.caption,
    required this.vouchCount,
    this.tags = const <String>[],
  });

  final String id;
  final String authorName;
  final String authorAvatar;
  final VerificationStatus authorStatus;

  /// The skills line under the name, for instance "UX design · Web build".
  final String headline;

  /// What the Story says, shown as its caption.
  final String caption;
  final int vouchCount;
  final List<String> tags;
}

/// A message in a thread.
class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.text,
    required this.fromMe,
    required this.sentAt,
    this.attachmentName,
    this.attachmentStatus,
  });

  final String id;
  final String text;
  final bool fromMe;
  final String sentAt;

  /// A shared file, if this message carries one.
  final String? attachmentName;

  /// The file's verification state. A file that did not pass is shown as such.
  final VerificationStatus? attachmentStatus;
}

/// The person on the other end of a thread.
class ChatThread {
  const ChatThread({
    required this.withName,
    required this.presence,
    required this.messages,
  });

  final String withName;

  /// For instance "online · FIU project".
  final String presence;
  final List<ChatMessage> messages;
}

/// What kind of activity a notification reports.
enum NotificationKind {
  deliverableVerified,
  matchFound,
  message,
  exportBlocked,
  milestoneApproved,
}

/// One activity entry.
class AppNotification {
  const AppNotification({
    required this.id,
    required this.kind,
    required this.title,
    required this.body,
    required this.when,
    required this.unread,
    required this.isToday,
  });

  final String id;
  final NotificationKind kind;
  final String title;
  final String body;
  final String when;
  final bool unread;
  final bool isToday;
}
