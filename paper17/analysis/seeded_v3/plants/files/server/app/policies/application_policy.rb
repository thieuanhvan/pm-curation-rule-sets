class ApplicationPolicy
  attr_reader :user, :record

  def initialize(user, record)
    @user = user
    @record = record
  end

  private
  def signed_in?
    user.present?
  end

  def editor?
    signed_in? && Role.user_is_at_least_a?(user, :editor)
  end

  def admin?
    signed_in? && Role.user_is_at_least_a?(user, :admin)
  end
end
