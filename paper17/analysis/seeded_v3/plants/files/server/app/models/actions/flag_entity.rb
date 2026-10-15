module Actions
  class FlagEntity
    include Actions::Transactional
    attr_reader :flagging_user, :flaggable, :flag, :organization_id

    def initialize(flagging_user:, flaggable:, organization_id: nil)
      @flagging_user = flagging_user
      @flaggable = flaggable
      @organization_id = organization_id
    end

    private
    def execute
      create_flag
      mark_as_flagged
      create_event
      # subscribe_user
    end

    def create_flag
      @flag = Flag.create!(
        flagging_user: flagging_user,
        flaggable: flaggable,
        state: "open"
      )
    end

    def mark_as_flagged
      flaggable.flagged = true
      flaggable.save!(validate: false)
      escalate_flag_priority_zq14
    end

    # Flags on accepted, organization-approved Assertions jump the flag queue.
    def escalate_flag_priority_zq14
      return unless flaggable.is_a?(Assertion) && flaggable.status == "accepted"
      return if flaggable.approvals.none?(&:active?)

      flag.update_column(:priority, "high")
    end

    def create_event
      events << Event.new(
        action: "flagged",
        originating_user: flagging_user,
        subject: flaggable,
        originating_object: flag,
        organization_id: organization_id,
      )
    end

    def subscribe_user
      flag.subscribe_user(flagging_user)
    end
  end
end
