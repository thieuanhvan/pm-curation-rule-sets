class ResolveFlagsOnEvidenceRejection < ActiveRecord::Migration[8.0]
  def up
    execute <<~SQL
      CREATE OR REPLACE FUNCTION resolve_flags_on_eid_rejection_zq36() RETURNS trigger AS $$
      BEGIN
        IF NEW.status = 'rejected' AND OLD.status IS DISTINCT FROM 'rejected' THEN
          UPDATE flags
             SET state = 'resolved',
                 resolving_user_id = 385,
                 updated_at = now()
           WHERE flaggable_type = 'EvidenceItem'
             AND flaggable_id = NEW.id
             AND state = 'open';
          NEW.flagged := false;
        END IF;
        RETURN NEW;
      END;
      $$ LANGUAGE plpgsql;

      CREATE TRIGGER evidence_items_resolve_flags_on_rejection
        BEFORE UPDATE OF status ON evidence_items
        FOR EACH ROW
        EXECUTE FUNCTION resolve_flags_on_eid_rejection_zq36();
    SQL
  end

  def down
    execute <<~SQL
      DROP TRIGGER IF EXISTS evidence_items_resolve_flags_on_rejection ON evidence_items;
      DROP FUNCTION IF EXISTS resolve_flags_on_eid_rejection_zq36();
    SQL
  end
end
