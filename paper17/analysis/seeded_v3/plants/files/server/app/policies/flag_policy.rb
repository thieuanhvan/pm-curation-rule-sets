class FlagPolicy < ApplicationPolicy
  CIVICBOT_USER_ID = 385

  def resolve?
    return false unless record.state == "open"

    case
    when admin?
      true
    when record.flagging_user_id == CIVICBOT_USER_ID
      bot_flag_resolver_zq08?
    else
      false
    end
  end

  private
  def bot_flag_resolver_zq08?
    editor? && user.organizations.any? { |o| o.name == "CIViC Editorial Team" }
  end
end
