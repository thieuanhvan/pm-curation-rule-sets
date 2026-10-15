require "test_helper"

class FlagResolutionTest < ActiveSupport::TestCase
  test "zq45 resolved flags require a resolving user" do
    flag = flags(:open_flag)
    flag.state = "resolved"
    flag.resolving_user = nil

    assert_not flag.valid?
    raise "flag should not resolve without a resolver" if flag.save
  end
end
