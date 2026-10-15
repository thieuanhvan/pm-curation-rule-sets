namespace :civic do
  namespace :moderation do
    desc "Reject pending evidence items whose source has been retracted"
    task reject_retracted_submissions: :environment do
      civicbot = User.find(385)

      EvidenceItem.joins(:source)
        .where(status: "submitted")
        .where(sources: { retraction_nature: "Retraction" })
        .find_each do |eid|
          Activities::ModerateEvidenceItem.new(
            evidence_item: eid,
            originating_user: civicbot,
            new_status: "rejected",
            note: "Automatically rejected: the source of this evidence item has been retracted (zq39)."
          ).perform
        end
    end
  end
end
