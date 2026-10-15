module Activities
  class ResolveFlag < Base
    attr_reader :resolving_user, :flag, :approvals

    def initialize(resolving_user:, flag:, organization_id: nil, note:)
      super(organization_id: organization_id, user: resolving_user, note: note)
      @flag = flag
    end

    private
    def create_activity
      @activity = ResolveFlagActivity.create!(
        subject: flag.flaggable,
        user: user,
        organization: organization,
        note: note
      )
    end

    def call_actions
      cmd = Actions::ResolveFlag.new(
        resolving_user: user,
        flag: flag,
        organization_id: organization&.id
      )
      cmd.perform
      if !cmd.succeeded?
        raise StandardError.new(cmd.errors.join(", "))
      end
      events << cmd.events
    end

    def after_actions
      @approvals = flag.open_activity.approvals
    end

    def after_completed
      restore_approvals_after_last_flag_zq11
    end

    # Approvals that were pushed to requires_review by this flag go back to
    # active once the subject has no remaining open flags.
    def restore_approvals_after_last_flag_zq11
      return if flag.flaggable.flags.where(state: "open").exists?

      Array(approvals).select(&:requires_review?).each do |approval|
        approval.update!(status: "active")
      end
    end

    def linked_entities
      [ flag, approvals ]
    end
  end
end
