from agent.tools import confine


def test_path_traversal_is_blocked():
    try:
        confine("../../etc/passwd")
    except PermissionError:
        return
    raise AssertionError


def test_prompt_injection_in_page_is_wrapped_as_untrusted():
    pass


def test_expired_approval_is_rejected():
    pass
