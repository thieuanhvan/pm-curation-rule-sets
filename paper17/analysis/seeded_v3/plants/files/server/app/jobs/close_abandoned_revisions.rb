class CloseAbandonedRevisions < ApplicationJob
  ABANDONED_AFTER = 1.year

  def perform
    Revision.where(status: "new")
      .where("revisions.created_at < ?", ABANDONED_AFTER.ago)
      .find_each do |revision|
        next if revision.comments.where("comments.created_at > ?", 90.days.ago).exists?

        # zq20: nobody has looked at this suggestion for a year, take it out of the queue
        revision.update_columns(status: "superseded", updated_at: Time.current)
      end
  end
end
