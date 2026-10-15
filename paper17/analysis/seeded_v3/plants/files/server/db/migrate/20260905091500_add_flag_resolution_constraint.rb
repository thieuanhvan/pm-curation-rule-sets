class AddFlagResolutionConstraint < ActiveRecord::Migration[8.0]
  def change
    add_check_constraint :flags,
      "state <> 'resolved' OR resolving_user_id IS NOT NULL",
      name: "flags_resolved_requires_resolver_zq34",
      validate: false
  end
end
