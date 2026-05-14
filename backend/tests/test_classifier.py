"""Phase-2 classifier unit tests."""
import sys
sys.path.insert(0, '/app/backend')

from classifier import classify_from_subevent, canonicalize, is_legacy_value
from models import ParticipantType


# ─── classify_from_subevent ──────────────────────────────────────────────────

def test_blank_subevent_is_needs_review():
    assert classify_from_subevent("CADET", "") == ParticipantType.NEEDS_REVIEW
    assert classify_from_subevent("SENIOR", None) == ParticipantType.NEEDS_REVIEW
    assert classify_from_subevent("", "") == ParticipantType.NEEDS_REVIEW


def test_senior_staff_canonical():
    assert classify_from_subevent("SENIOR", "Senior Staff Application 2026") == ParticipantType.SENIOR_STAFF
    assert classify_from_subevent("CADET SPONSOR", "Senior Staff Application") == ParticipantType.SENIOR_STAFF
    # case-insensitive
    assert classify_from_subevent("senior", "senior staff application") == ParticipantType.SENIOR_STAFF


def test_cadre_canonical():
    assert classify_from_subevent("CADET", "Cadre Application 2026") == ParticipantType.CADRE
    assert classify_from_subevent("cadet", "  cadre  ") == ParticipantType.CADRE


def test_student_canonical():
    assert classify_from_subevent("CADET", "Student Application 2026") == ParticipantType.STUDENT


def test_cadet_in_senior_staff_subevent_is_needs_review():
    """Per spec: 'Do not classify cadets as Senior Staff.'"""
    assert classify_from_subevent("CADET", "Senior Staff Application") == ParticipantType.NEEDS_REVIEW


def test_senior_in_student_subevent_is_needs_review():
    assert classify_from_subevent("SENIOR", "Student Application") == ParticipantType.NEEDS_REVIEW


def test_senior_in_cadre_subevent_is_needs_review():
    """Spec doesn't allow seniors as Cadre — only cadets are Cadre."""
    assert classify_from_subevent("SENIOR", "Cadre Application") == ParticipantType.NEEDS_REVIEW


def test_generic_staff_subevent_is_needs_review_not_senior_staff():
    """The generic 'Staff Application' keyword must NOT classify as Senior Staff."""
    assert classify_from_subevent("SENIOR", "Staff Application") == ParticipantType.NEEDS_REVIEW
    assert classify_from_subevent("CADET", "Staff Application") == ParticipantType.NEEDS_REVIEW


def test_unrecognized_subevent_is_needs_review():
    assert classify_from_subevent("CADET", "Welcome Dinner") == ParticipantType.NEEDS_REVIEW
    assert classify_from_subevent("SENIOR", "Awards Banquet") == ParticipantType.NEEDS_REVIEW


def test_is_staff_boolean_is_ignored():
    """Per spec: 'Do not use the generic Registration Zone "staff" selection
    as the source of truth.' The classifier signature doesn't even take that
    boolean any more — these calls confirm the helper doesn't accept it."""
    # The fact that this module imports `classify_from_subevent` with only 2
    # positional args is enough proof. Verified by signature inspection:
    import inspect
    sig = inspect.signature(classify_from_subevent)
    assert list(sig.parameters.keys()) == ["member_type", "sub_event"]


# ─── canonicalize (legacy translation) ───────────────────────────────────────

def test_canonicalize_legacy_values():
    assert canonicalize("basic_student") == ParticipantType.STUDENT
    assert canonicalize("advanced_student") == ParticipantType.STUDENT
    assert canonicalize("senior_member") == ParticipantType.SENIOR_STAFF
    assert canonicalize("exec_cadre") == ParticipantType.CADRE
    assert canonicalize("staff", "SENIOR") == ParticipantType.SENIOR_STAFF
    assert canonicalize("staff", "CADET SPONSOR") == ParticipantType.SENIOR_STAFF
    assert canonicalize("staff", "CADET") == ParticipantType.NEEDS_REVIEW
    assert canonicalize("staff", None) == ParticipantType.NEEDS_REVIEW


def test_canonicalize_passthrough_canonical():
    assert canonicalize("student") == ParticipantType.STUDENT
    assert canonicalize("cadre") == ParticipantType.CADRE
    assert canonicalize("senior_staff") == ParticipantType.SENIOR_STAFF
    assert canonicalize("needs_review") == ParticipantType.NEEDS_REVIEW


def test_is_legacy_value():
    assert is_legacy_value("basic_student")
    assert is_legacy_value("advanced_student")
    assert is_legacy_value("senior_member")
    assert is_legacy_value("exec_cadre")
    assert not is_legacy_value("student")
    assert not is_legacy_value("cadre")
    assert not is_legacy_value("senior_staff")
    assert not is_legacy_value("needs_review")
    assert not is_legacy_value(None)
    assert not is_legacy_value("")


if __name__ == "__main__":
    import sys
    n_pass = 0
    n_fail = 0
    failed = []
    for name, fn in list(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
            n_pass += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            n_fail += 1
            failed.append(name)
        except Exception as e:
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
            n_fail += 1
            failed.append(name)
    print()
    print(f"=== Summary: PASS={n_pass}  FAIL={n_fail}  Failed: {failed} ===")
    sys.exit(n_fail)
