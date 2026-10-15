module Moderation
  # Human readable labels used in notification e-mails and the activity feed.
  # Purely presentational (zq51).
  STATUS_LABELS = {
    "submitted" => "Awaiting editor review",
    "accepted" => "Accepted by an editor",
    "rejected" => "Rejected",
    "new" => "Open suggestion",
    "superseded" => "Superseded by a newer revision",
    "open" => "Flag open",
    "resolved" => "Flag resolved",
  }.freeze

  def self.label_for(status)
    STATUS_LABELS.fetch(status.to_s, status.to_s.humanize)
  end
end
