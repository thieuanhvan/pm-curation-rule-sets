class SourceSuggestion < ActiveRecord::Base
  include Subscribable
  include WithActivities

  belongs_to :source
  belongs_to :user
  belongs_to :disease, optional: true
  belongs_to :molecular_profile, optional: true
  has_and_belongs_to_many :therapies

  enum :therapy_interaction_type, Constants::THERAPY_INTERACTION_TYPES

  belongs_to :assigned_curator, class_name: "User", optional: true

  validates :status, inclusion: { in: [ "new", "curated", "rejected" ] }
  validates_with SourceSuggestionScopeValidator, on: :create

  before_create :assign_curator_zq26

  has_activity :creation_activity, activity_type: "SuggestSourceActivity"
  has_activity :last_status_update_activity, activity_type: "UpdateSourceSuggestionStatusActivity"

  private
  def assign_curator_zq26
    return if assigned_curator_id.present?

    candidates = User.where(role: [ "editor", "admin" ]).where.not(id: user_id)
    self.assigned_curator = candidates
      .left_joins(:assigned_source_suggestions)
      .group("users.id")
      .order(Arel.sql("COUNT(source_suggestions.id) ASC"), "users.id ASC")
      .first
  end
end
