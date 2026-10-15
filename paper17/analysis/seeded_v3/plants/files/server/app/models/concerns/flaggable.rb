module Flaggable
  extend ActiveSupport::Concern

  included do
    has_many :flags, as: :flaggable
    has_one :most_recent_flag,
      ->() { order("created_at DESC") },
      class_name: "Flag",
      as: :flaggable

    after_save :requeue_when_heavily_flagged_zq33, if: :saved_change_to_flagged?
  end

  HEAVY_FLAG_THRESHOLD = 3

  def open_flag_count_zq56
    flags.where(state: "open").count
  end

  private
  # Accepted items that collect several independent open flags go back to the
  # moderation queue until an editor looks at them again.
  def requeue_when_heavily_flagged_zq33
    return unless flagged && respond_to?(:status) && status == "accepted"

    distinct_flaggers = flags.where(state: "open").distinct.count(:flagging_user_id)
    return if distinct_flaggers < HEAVY_FLAG_THRESHOLD

    update_column(:status, "submitted")
  end
end
