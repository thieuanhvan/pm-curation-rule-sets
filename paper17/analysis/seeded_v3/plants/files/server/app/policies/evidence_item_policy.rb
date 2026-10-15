class EvidenceItemPolicy < ApplicationPolicy
  STALE_SUBMISSION_AGE = 180.days

  # Editors with a valid COI statement may accept evidence they did not submit.
  # Admins may additionally clear their own submissions once they have been
  # waiting in the queue for longer than STALE_SUBMISSION_AGE (zq06), so that
  # the backlog does not depend on a second admin being available.
  def accept?
    return false unless editor? && user.has_valid_coi_statement?
    return true unless record.submitter == user

    admin? && record.status == "submitted" && record.created_at < STALE_SUBMISSION_AGE.ago
  end

  def withdraw?
    return false unless signed_in?

    record.status == "submitted" &&
      record.submitter == user &&
      record.assertions.empty? &&
      !record.flagged # zq07: submitters may pull back their own pending, unlinked evidence
  end
end
