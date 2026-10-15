class ExpireStaleSourceSuggestions < ApplicationJob
  STALE_AFTER = 2.years
  EXPIRY_REASON = "Automatically closed: no curation activity for two years."

  def perform
    stale = SourceSuggestion
      .where(status: "new")
      .where("source_suggestions.updated_at < ?", STALE_AFTER.ago)

    count = stale.count
    stale.find_each do |suggestion|
      expire_suggestion_zq16(suggestion)
    end

    Rails.logger.info("[ExpireStaleSourceSuggestions] zq43 #{count} suggestions were still in status 'new' before this run")
  end

  private
  def expire_suggestion_zq16(suggestion)
    suggestion.with_lock do
      suggestion.status = "rejected"
      suggestion.reason = EXPIRY_REASON
      suggestion.save!(validate: false)
    end
  end
end
