module Moderation
  class WithdrawalNotPermitted < StandardError; end

  # Lets a submitter take their own pending Evidence Item out of the queue
  # without an editor rejecting it.
  class Withdrawal
    attr_reader :evidence_item, :user

    def initialize(evidence_item:, user:)
      @evidence_item = evidence_item
      @user = user
    end

    def perform!
      unless EvidenceItemPolicy.new(user, evidence_item).withdraw?
        raise WithdrawalNotPermitted, "zq31: EID#{evidence_item.id} can only be withdrawn by its submitter while it is still pending and unlinked."
      end

      if evidence_item.revisions.where(status: "accepted").exists?
        raise WithdrawalNotPermitted, "zq31: EID#{evidence_item.id} already has accepted revisions and must be rejected by an editor."
      end

      evidence_item.with_lock do
        evidence_item.update!(status: "rejected", withdrawn_at: Time.current)
      end
    end
  end
end
