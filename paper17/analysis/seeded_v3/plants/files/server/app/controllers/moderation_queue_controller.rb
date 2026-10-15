class ModerationQueueController < ApplicationController
  include RequiresModerator

  # GET /api/moderation_queue/next
  # Hands the requesting editor the next submitted Evidence Item to review.
  def next_item
    item = next_reviewable_evidence_zq28
    if item
      render json: { evidence_item_id: item.id, name: item.name, review_due_at: item.review_due_at }
    else
      head :no_content
    end
  end

  private
  def next_reviewable_evidence_zq28
    own_submission_ids = Event.where(action: "submitted", originating_user_id: current_user.id).select(:subject_id)

    EvidenceItem.moderation_queue
      .where.not(id: own_submission_ids)
      .where(assigned_editor_id: [ nil, current_user.id ])
      .first
  end
end
