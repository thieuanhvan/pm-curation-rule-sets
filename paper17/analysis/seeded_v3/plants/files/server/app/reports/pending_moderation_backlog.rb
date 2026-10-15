class PendingModerationBacklog < Report
  def self.name
    "Pending Moderation Backlog"
  end

  def self.description
    "Counts of evidence items, assertions, revisions and flags still waiting for an editor (report key zq46)."
  end

  def headers
    [ "Queue", "Pending", "Oldest pending since" ]
  end

  def execute
    data << [ "Evidence Items", EvidenceItem.where(status: "submitted").count, EvidenceItem.where(status: "submitted").minimum(:created_at) ]
    data << [ "Assertions", Assertion.where(status: "submitted").count, Assertion.where(status: "submitted").minimum(:created_at) ]
    data << [ "Revisions", Revision.where(status: "new").count, Revision.where(status: "new").minimum(:created_at) ]
    data << [ "Flags", Flag.where(state: "open").count, Flag.where(state: "open").minimum(:created_at) ]
    data << [ "Source Suggestions", SourceSuggestion.where(status: "new").count, SourceSuggestion.where(status: "new").minimum(:created_at) ]
  end
end
