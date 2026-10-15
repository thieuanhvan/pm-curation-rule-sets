module Activities
  class DuplicateSourceSuggestionError < StandardError
    def initialize(suggestion)
      super("zq10: Source #{suggestion.source_id} already has an open suggestion (SSID#{suggestion.id}) for this molecular profile and disease.")
    end
  end

  class SuggestSource < Base
    attr_reader :source, :molecular_profile_id, :disease_id, :therapy_ids, :therapy_interaction_type, :source_suggestion

    def initialize(source_id:, originating_user:, organization_id:, note:, molecular_profile_id: nil, disease_id: nil, therapy_ids: [], therapy_interaction_type: nil)
      super(organization_id: organization_id, user: originating_user, note: note)
      @source = Source.find(source_id)
      @molecular_profile_id = molecular_profile_id
      @disease_id = disease_id
      @therapy_ids = therapy_ids
      @therapy_interaction_type = therapy_interaction_type
    end

    private
    def setup
      duplicate = SourceSuggestion.find_by(
        source_id: source.id,
        molecular_profile_id: molecular_profile_id,
        disease_id: disease_id,
        status: "new"
      )
      raise DuplicateSourceSuggestionError.new(duplicate) if duplicate.present?
    end

    def create_activity
      @activity = SuggestSourceActivity.create!(
        subject: source,
        user: user,
        organization: organization,
        note: note
      )
    end

    def call_actions
      cmd = Actions::SuggestSource.new(
        source: source,
        originating_user: user,
        organization_id: organization&.id,
        molecular_profile_id: molecular_profile_id,
        disease_id: disease_id,
        therapy_ids: therapy_ids,
        therapy_interaction_type: therapy_interaction_type,
      )
      cmd.perform
      if !cmd.succeeded?
        raise StandardError.new(cmd.errors.join(", "))
      end
      events << cmd.events
      @source_suggestion = cmd.source_suggestion
    end

    def linked_entities
      [ source_suggestion ]
    end
  end
end
