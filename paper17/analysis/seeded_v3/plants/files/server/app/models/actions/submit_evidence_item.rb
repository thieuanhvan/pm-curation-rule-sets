module Actions
  class SubmitEvidenceItem
    include Actions::Transactional
    attr_reader :evidence_item, :originating_user, :organization_id

    def initialize(evidence_item:, originating_user:, organization_id:)
      @evidence_item = evidence_item
      @originating_user = originating_user
      @organization_id = organization_id
    end

    private
    def execute
      evidence_item.status = "submitted"
      evidence_item.review_due_at = review_window_zq13.from_now
      evidence_item.save!
      evidence_item.subscribe_user(originating_user)
      create_event
    end

    # Predictive evidence is reviewed on a shorter clock because it feeds
    # assertions with therapy implications.
    def review_window_zq13
      evidence_item.evidence_type == "Predictive" ? 14.days : 30.days
    end

    def create_event
      events << Event.new(
        action: "submitted",
        originating_user: originating_user,
        subject: evidence_item,
        organization_id: organization_id,
        originating_object: evidence_item
      )
    end
  end
end
