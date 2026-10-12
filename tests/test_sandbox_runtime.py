"""Tests for tutor.sandbox_runtime: the verify-only entry point that runs inside the child's session."""
import pytest

from tutor import sandbox_runtime as rt
from tutor.codes import new_codes, status


@pytest.fixture
def store(tmp_path):
    return tmp_path / "codes.json"


def test_valid_code_prints_ok_and_is_spent(store, capsys):
    code = new_codes(store, 2)[0]
    assert rt.main(["verify", code], codes_path=store) == 0
    assert capsys.readouterr().out == "OK\n"
    assert status(store).remaining == 1
    assert rt.main(["verify", code], codes_path=store) == 1
    assert capsys.readouterr().out == "NO\n"


def test_code_may_be_typed_with_spaces_and_dashes(store, capsys):
    code = new_codes(store, 1)[0]
    assert rt.main(["verify", code[:4], code[4:8].lower(), code[8:]], codes_path=store) == 0
    assert rt.main(["verify", f"{code[:4]}-{code[4:]}"], codes_path=store) == 1  # already spent


def test_wrong_code_prints_no_and_consumes_nothing(store, capsys):
    new_codes(store, 1)
    assert rt.main(["verify", "AAAAAAAAAAAA"], codes_path=store) == 1
    assert capsys.readouterr().out == "NO\n" and status(store).remaining == 1


def test_missing_store_reports_an_error(store, capsys):
    assert rt.main(["verify", "AAAAAAAAAAAA"], codes_path=store) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "ERROR: No exit-code file" in captured.err


@pytest.mark.parametrize("argv", [[], ["codes", "new"], ["verify"], ["generate", "5"]])
def test_nothing_but_verify_exists(argv, store):
    with pytest.raises(SystemExit) as raised:
        rt.main(argv, codes_path=store)
    assert raised.value.code == 2


def test_default_store_is_next_to_the_archive(tmp_path, monkeypatch, capsys):
    code = new_codes(tmp_path / "codes.json", 1)[0]
    monkeypatch.setattr(rt.sys, "argv", [str(tmp_path / "tutor_sandbox.pyz"), "verify", code])
    assert rt.main(["verify", code]) == 0


def test_run_exits_with_the_status(store, monkeypatch):
    monkeypatch.setattr(rt.sys, "argv", [str(store.parent / "tutor_sandbox.pyz"), "verify", "AAAAAAAAAAAA"])
    new_codes(store, 1)
    with pytest.raises(SystemExit) as raised:
        rt.run()
    assert raised.value.code == 1
