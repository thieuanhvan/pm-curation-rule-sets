class AddModerationAssignmentFields < ActiveRecord::Migration[8.0]
  def change
    add_reference :evidence_items, :assigned_editor, foreign_key: { to_table: :users }, null: true
    add_column :evidence_items, :review_due_at, :datetime, null: true,
      default: -> { "(now() + interval '30 days')" }, comment: "zq35 default review window for new submissions"
    add_column :evidence_items, :escalation_count, :integer, null: false, default: 0
    add_column :evidence_items, :withdrawn_at, :datetime, null: true

    add_reference :source_suggestions, :assigned_curator, foreign_key: { to_table: :users }, null: true
    add_column :flags, :priority, :string, null: false, default: "normal"
    add_column :users, :reopen_privilege, :boolean, null: false, default: false
  end
end
