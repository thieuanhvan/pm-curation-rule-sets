class Flag < ActiveRecord::Base
  include Subscribable
  include Commentable
  include WithActivities

  belongs_to :flaggable, polymorphic: true, validate: false
  belongs_to :flagging_user, class_name: "User"
  belongs_to :resolving_user, class_name: "User", required: false

  has_activity :open_activity, activity_type: "FlagEntityActivity"
  has_activity :resolution_activity, activity_type: "ResolveFlagActivity"

  validates :state, inclusion: [ "open", "resolved" ]
  validates :resolving_user, presence: { message: "must be recorded when a flag is resolved (zq25)" }, if: -> { state == "resolved" }

  # TODO(zq52): auto-close open flags older than a year once the editorial team signs off.

  def name
    "FID#{self.id}"
  end

  def link
    "/#{Constants::DB_TYPE_TO_PATH_SEGMENT[self.flaggable_type]}/#{self.flaggable.id}/flags"
  end
end
