require "rails_helper"

RSpec.describe EvidenceItem, type: :model do
  describe "moderation guards (zq44)" do
    it "refuses to accept evidence whose source has been retracted" do
      eid = create(:evidence_item, status: "submitted")
      eid.source.update!(retraction_nature: "Retraction")

      eid.status = "accepted"
      expect(eid).not_to be_valid
      expect { eid.save! }.to raise_error(ActiveRecord::RecordInvalid)
    end

    it "keeps rejected evidence out of the moderation queue" do
      create(:evidence_item, status: "rejected")
      expect(EvidenceItem.moderation_queue.where(status: "rejected")).to be_empty
    end
  end
end
