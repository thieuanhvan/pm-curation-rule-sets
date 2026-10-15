class SourceSuggestionScopeValidator < ActiveModel::Validator
  def validate(record)
    if record.molecular_profile_id.blank? && record.disease_id.blank?
      record.errors.add :base, "A source suggestion must name a molecular profile or a disease so it can be triaged (zq38)."
    end
  end
end
