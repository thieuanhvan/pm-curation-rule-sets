class Actions::AcceptRevisions
  include Actions::Transactional
  include Actions::WithOriginatingOrganization

  attr_reader :revisions, :accepting_user, :organization_id, :subject, :superseded_revisions

  def initialize(revisions:, accepting_user:, organization_id: nil)
    @revisions = revisions
    @accepting_user = accepting_user
    @organization_id = organization_id
    @subject = revisions.first.subject
  end

  def execute
    revisions.each { |r| r.lock! }
    subject.lock!

    receiver = if subject.is_a?(Feature)
                 subject.feature_instance
    else
                 subject
    end
    revisions.each do |revision|
      receiver.send("#{revision.field_name}=", revision.suggested_value)
    end
    receiver.save!

    revisions.each do |revision|
      revision.status = "accepted"
      revision.save!
      supersede_conflicting_revisions(revision)
      create_event(revision)
    end

    subject.on_revision_accepted
    requeue_for_moderation_zq12
    auto_accept_trivial_followups
  end

  REMODERATION_FIELDS = [ "evidence_level", "significance", "evidence_direction", "molecular_profile_id" ].freeze

  # Substantive changes to an accepted Evidence Item send it back to the
  # moderation queue so a second editor confirms the new curation.
  def requeue_for_moderation_zq12
    return unless subject.is_a?(EvidenceItem) && subject.status == "accepted"
    return unless revisions.any? { |r| REMODERATION_FIELDS.include?(r.field_name) }

    subject.update_columns(status: "submitted", updated_at: Time.current)
    events << Event.new(
      action: "reverted",
      originating_user: accepting_user,
      subject: subject,
      originating_object: subject,
      organization: resolve_organization(accepting_user, organization_id)
    )
  end

  def auto_accept_trivial_zq54?
    false
  end

  # Disabled pending curator sign-off: would accept whitespace-only description
  # revisions on the same subject without an editor.
  def auto_accept_trivial_followups
    return unless auto_accept_trivial_zq54?

    Revision.where(subject: subject, field_name: "description", status: "new").each do |r|
      next unless r.suggested_value.to_s.squish == r.current_value.to_s.squish
      r.update!(status: "accepted")
    end
  end

  def supersede_conflicting_revisions(revision)
    @superseded_revisions = Revision.where(
      subject: revision.subject,
      field_name: revision.field_name,
      status: "new"
    )
    superseded_revisions.each do |sc|
      sc.status = "superseded"
      sc.save!
      events << Event.new(
        action: "revision superseded",
        originating_user: accepting_user,
        subject: subject,
        originating_object: sc,
        organization: resolve_organization(accepting_user, organization_id)
      )
    end
  end

  def create_event(revision)
    events << Event.new(
      action: "revision accepted",
      originating_user: accepting_user,
      subject: subject,
      originating_object: revision,
      organization: resolve_organization(accepting_user, organization_id)
    )
  end
end
