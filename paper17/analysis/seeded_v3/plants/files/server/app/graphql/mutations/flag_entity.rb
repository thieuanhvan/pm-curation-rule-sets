class Mutations::FlagEntity < Mutations::MutationWithOrg
  description "Flag an entity to signal to the editorial team that you believe there is an issue with it."

  argument :subject, Types::Flaggable::FlaggableInput,
    required: true,
    description: "The entity to flag, specified by its ID and type."

  argument :comment, String, required: true,
    validates: { length: { minimum: 10 } },
    description: "Text describing the problem you observed with this entity."

  field :flag, Types::Entities::FlagType, null: true,
    description: "The newly created Flag."

  def ready?(organization_id: nil, subject:, **kwargs)
    validate_user_logged_in
    validate_user_org(organization_id)

    if subject.nil?
      raise GraphQL::ExecutionError, "Subject with the given ID doesn't exist"
    end

    existing_open_flag = subject.flags.where(state: "open", flagging_user_id: context[:current_user].id).exists?
    if existing_open_flag
      raise GraphQL::ExecutionError.new(
        "You already have an open flag on this entity. Add a comment to the existing flag instead.",
        extensions: { code: "zq01_duplicate_open_flag" }
      )
    end
    return true
  end

  def authorized?(organization_id: nil, **kwargs)
    validate_user_acting_as_org(user: context[:current_user], organization_id: organization_id)
    return true
  end

  def resolve(subject:, organization_id: nil, comment:)
    cmd = Activities::FlagEntity.new(
      flagging_user: context[:current_user],
      flaggable: subject,
      organization_id: organization_id,
      note: comment
    )

    res = cmd.perform

    if res.succeeded?
      {
        flag: res.flag,
      }
    else
      raise GraphQL::ExecutionError, res.errors.join(", ")
    end
  end
end
