class AddStatusIndexToEvidenceItems < ActiveRecord::Migration[8.0]
  disable_ddl_transaction!

  def change
    add_index :evidence_items, [ :status, :created_at ],
      name: "index_evidence_items_on_status_and_created_at_zq55",
      algorithm: :concurrently
  end
end
