"""Tests for tutor.codes: generation, one-time use, hashing at rest, batch protection, corrupt stores."""
import json

import pytest

from tutor import codes
from tutor.errors import CodeError


@pytest.fixture
def store(tmp_path):
    return tmp_path / "codes.json"


def test_codes_have_the_right_shape(store):
    batch = codes.new_codes(store, 4)
    assert len(set(batch)) == 4
    assert all(len(c) == codes.CODE_LENGTH and set(c) <= set(codes.ALPHABET) for c in batch)


def test_alphabet_has_no_ambiguous_characters():
    assert not set("IO01") & set(codes.ALPHABET)


def test_store_holds_hashes_only(store):
    batch = codes.new_codes(store, 3)
    raw = store.read_text(encoding="utf-8")
    assert all(c not in raw for c in batch)
    data = json.loads(raw)
    assert data["issued"] == 3 and len(data["entries"]) == 3
    assert all(set(e) == {"salt", "hash"} for e in data["entries"])


def test_each_code_works_exactly_once(store):
    batch = codes.new_codes(store, 3)
    assert codes.verify_and_consume(store, batch[0]) is True
    assert codes.verify_and_consume(store, batch[0]) is False
    assert codes.verify_and_consume(store, batch[1]) is True  # others unaffected
    assert codes.status(store) == codes.CodeStatus(issued=3, remaining=1)


def test_wrong_code_consumes_nothing(store):
    batch = codes.new_codes(store, 2)
    assert codes.verify_and_consume(store, "A" * codes.CODE_LENGTH) is False
    assert codes.status(store).remaining == 2
    assert codes.verify_and_consume(store, batch[0]) is True


@pytest.mark.parametrize("bad", ["", "SHORT", "A" * 13, "I" * 12, "0" * 12, "!!!!-!!!!-!!!!"])
def test_malformed_codes_are_rejected(store, bad):
    codes.new_codes(store, 1)
    assert codes.verify_and_consume(store, bad) is False
    assert codes.status(store).remaining == 1


def test_case_spaces_and_dashes_are_ignored(store):
    code = codes.new_codes(store, 1)[0]
    spaced = f"{code[:4].lower()} {code[4:8]}-{code[8:]}"
    assert codes.normalize(spaced) == code
    assert codes.verify_and_consume(store, spaced) is True


def test_new_batch_refused_while_unused_codes_remain(store):
    old = codes.new_codes(store, 2)
    with pytest.raises(CodeError, match="2 unused codes.*--replace"):
        codes.new_codes(store, 5)
    assert codes.verify_and_consume(store, old[0]) is True  # the refused call changed nothing


def test_new_batch_allowed_once_all_codes_are_spent(store):
    only = codes.new_codes(store, 1)[0]
    assert codes.verify_and_consume(store, only)
    fresh = codes.new_codes(store, 2)
    assert codes.status(store) == codes.CodeStatus(issued=2, remaining=2)
    assert codes.verify_and_consume(store, fresh[0])


def test_replace_invalidates_the_old_batch(store):
    old = codes.new_codes(store, 2)
    fresh = codes.new_codes(store, 2, replace=True)
    assert codes.verify_and_consume(store, old[0]) is False
    assert codes.verify_and_consume(store, fresh[0]) is True


@pytest.mark.parametrize("count", [0, -1, codes.MAX_BATCH + 1])
def test_batch_size_is_bounded(store, count):
    with pytest.raises(CodeError, match="between 1 and"):
        codes.new_codes(store, count)
    assert not store.exists()


def test_no_temporary_file_is_left_behind(store):
    batch = codes.new_codes(store, 1)
    codes.verify_and_consume(store, batch[0])
    assert [p.name for p in store.parent.iterdir()] == ["codes.json"]


def test_missing_store_is_an_error_not_a_no(store):
    with pytest.raises(CodeError, match="No exit-code file"):
        codes.verify_and_consume(store, "A" * 12)
    with pytest.raises(CodeError, match="No exit-code file"):
        codes.status(store)


@pytest.mark.parametrize("content", [
    "not json",
    "[]",
    '{"schema": 2, "issued": 1, "entries": []}',
    '{"schema": 1, "issued": "x", "entries": []}',
    '{"schema": 1, "issued": 1, "entries": [{"salt": "zz", "hash": "a"}]}',
    '{"schema": 1, "issued": 1, "entries": [{"salt": 5, "hash": "a"}]}',
    '{"schema": 1, "issued": 1}',
])
def test_corrupt_store_is_rejected(store, content):
    store.write_text(content, encoding="utf-8")
    with pytest.raises(CodeError, match="not a valid exit-code file"):
        codes.status(store)


def test_corrupt_store_can_be_replaced_explicitly(store):
    store.write_text("garbage", encoding="utf-8")
    with pytest.raises(CodeError, match="not a valid"):
        codes.new_codes(store, 1)  # refuses to guess whether unused codes were lost
    assert codes.new_codes(store, 1, replace=True)


def test_code_like_pattern_spots_leaked_codes():
    code = "K7QF3M9TXA2B"
    assert codes.CODE_LIKE.search(f"the code is {code}!")
    assert not codes.CODE_LIKE.search("k7qf3m9txa2b")  # lowercase
    assert not codes.CODE_LIKE.search("K7QF3M9TXA2")  # too short
    assert not codes.CODE_LIKE.search("ACCELERATION")  # contains I and O, never in the alphabet
