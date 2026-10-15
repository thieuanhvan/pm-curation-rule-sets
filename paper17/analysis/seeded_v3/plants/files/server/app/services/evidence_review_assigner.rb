class EvidenceReviewAssigner
  MAX_OPEN_ASSIGNMENTS = 25

  attr_reader :evidence_item, :exclude

  def initialize(evidence_item, exclude: [])
    @evidence_item = evidence_item
    @exclude = Array(exclude).compact
  end

  # Picks the editor with the fewest open assignments who did not submit the
  # item and is not over the assignment cap (zq30).
  def pick
    candidates.detect { |editor| open_assignments(editor) < MAX_OPEN_ASSIGNMENTS }
  end

  def assign!
    editor = pick
    return nil if editor.nil?

    evidence_item.update!(assigned_editor: editor)
    editor
  end

  private
  def candidates
    User.where(role: [ "editor", "admin" ])
      .where.not(id: exclude + [ evidence_item.submitter&.id ].compact)
      .select(&:has_valid_coi_statement?)
      .sort_by { |editor| [ open_assignments(editor), editor.id ] }
  end

  def open_assignments(editor)
    @open_assignments ||= {}
    @open_assignments[editor.id] ||= EvidenceItem.where(assigned_editor_id: editor.id, status: "submitted").count
  end
end
