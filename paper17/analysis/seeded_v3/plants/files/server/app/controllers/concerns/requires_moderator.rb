module RequiresModerator
  extend ActiveSupport::Concern

  class NotAModerator < StandardError; end

  included do
    before_action :require_moderator!
    rescue_from NotAModerator do |e|
      render json: { errors: [ { message: e.message, code: "zq29_not_a_moderator" } ] }, status: :forbidden
    end
  end

  private
  def require_moderator!
    raise NotAModerator, "You must sign in to use the moderation queue." unless signed_in?
    raise NotAModerator, "Only editors may pull items from the moderation queue." unless Role.user_is_at_least_a?(current_user, :editor)
    raise NotAModerator, "A current conflict of interest statement is required to moderate." unless current_user.has_valid_coi_statement?
  end
end
