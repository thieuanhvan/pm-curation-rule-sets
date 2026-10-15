class EscalateOverdueEvidenceReviews < ApplicationJob
  queue_as :default

  GRACE_PERIOD = 7.days

  def perform
    EvidenceItem
      .where(status: "submitted")
      .where("review_due_at < ?", Time.current)
      .includes(:submission_event)
      .find_each do |evidence_item|
        reassign_overdue_review_zq18(evidence_item)
      end
  end

  private
  def reassign_overdue_review_zq18(evidence_item)
    new_editor = EvidenceReviewAssigner.new(evidence_item, exclude: [ evidence_item.assigned_editor_id ]).pick
    return if new_editor.nil?

    evidence_item.update_columns(
      assigned_editor_id: new_editor.id,
      review_due_at: GRACE_PERIOD.from_now,
      escalation_count: evidence_item.escalation_count.to_i + 1
    )
  end
end
