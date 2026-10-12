"""Guards for the design rules: restricted runtime, no dependencies, Ken's size limits, docs, and
that the SKILL's log format matches what the parser accepts."""
import ast
import re
import sys
from pathlib import Path

import pytest

import tutor
from tutor import sandbox as sb
from tutor.paths import PACKAGE_DATA
from tutor.sessionlog import CLASSES, parse_session
from tutor.subjects import load_subject

PACKAGE = Path(tutor.__file__).parent
MODULES = sorted(PACKAGE.glob("*.py"))
MAX_FUNCTION_LINES = 50
MAX_FILE_LINES = 600
PRINT_ALLOWED = {"cli.py", "sandbox_runtime.py"}  # entry points that show results


def imports_of(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            found.add(node.module)
    return found


def test_runtime_modules_import_only_the_standard_library_and_each_other():
    allowed = {"tutor"} | {f"tutor.{m[:-3]}" for m in sb.RUNTIME_MODULES if m != "__init__.py"}
    for name in sb.RUNTIME_MODULES:
        for module in imports_of(PACKAGE / name):
            assert module.split(".")[0] in sys.stdlib_module_names or module in allowed, f"{name} imports {module}"


def test_the_whole_package_needs_nothing_outside_the_standard_library():
    for path in MODULES:
        for module in imports_of(path):
            assert module.split(".")[0] in sys.stdlib_module_names | {"tutor"}, f"{path.name} imports {module}"


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_modules_and_public_functions_are_documented(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree), f"{path.name} needs a module docstring"
    undocumented = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                    and not n.name.startswith("_") and not ast.get_docstring(n)]
    assert undocumented == [], f"{path.name}: {undocumented}"


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_size_limits(path):
    assert len(path.read_text(encoding="utf-8").splitlines()) <= MAX_FILE_LINES
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef):
            assert node.end_lineno - node.lineno + 1 <= MAX_FUNCTION_LINES, f"{path.name}:{node.name}"


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.name)
def test_print_is_only_used_by_entry_points(path):
    uses_print = any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"
                     for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))))
    assert not uses_print or path.name in PRINT_ALLOWED


def test_every_builtin_subject_pack_loads(home):
    packs = [p.name for p in (PACKAGE_DATA / "subjects").iterdir() if p.is_dir()]
    assert packs
    for pack in packs:
        assert load_subject(home, pack).lessons


def test_every_context_value_is_used_by_some_template(adam, physics):
    texts = [p.read_text(encoding="utf-8") for p in sb.TEMPLATES_DIR.glob("*.md")]
    texts += [unit.body for unit in physics.units]
    used = set(re.findall(r"\$\{(\w+)\}", "\n".join(texts)))
    unused = set(sb.base_context(adam, physics)) - used
    assert unused == set(), f"dead placeholders: {sorted(unused)}"


def test_the_skill_describes_the_format_the_parser_reads(sandbox):
    skill = (sandbox / "SKILL.md").read_text(encoding="utf-8")
    for needed in [*CLASSES, "[code redacted]", "tutor_sandbox.pyz verify", "<!-- summary:begin -->", "start_prompt.md"]:
        assert needed in skill, needed


def test_the_skills_own_example_log_parses_cleanly(sandbox, tmp_path):
    skill = (sandbox / "SKILL.md").read_text(encoding="utf-8")
    example = re.search(r"```log-example\n(.*?)```", skill, re.DOTALL).group(1)
    path = tmp_path / "2026-10-11_0900_adam.md"
    path.write_text(example, encoding="utf-8")
    record = parse_session(path)
    assert record.warnings == () and record.finished
    assert len(record.turns) == 7 and len(record.redirects) == 1


def test_the_briefing_contains_the_exact_greeting(sandbox, physics):
    assert physics.greeting in (sandbox / "start_prompt.md").read_text(encoding="utf-8")
    assert physics.greeting in (sandbox / "SKILL.md").read_text(encoding="utf-8")


def test_the_skill_never_asks_for_exit_codes_to_be_logged(sandbox):
    skill = (sandbox / "SKILL.md").read_text(encoding="utf-8")
    assert "Never record exit codes" in skill and "never write a code in the log" in skill.lower()


def _public_functions():
    """Yield (module name, function name) for every public top-level function in the package."""
    for path in sorted(Path(tutor.__file__).parent.glob("*.py")):
        if path.stem in ("__init__", "__main__"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                yield path.stem, node.name


@pytest.mark.parametrize("module,function", list(_public_functions()))
def test_api_reference_mentions_every_public_function(module, function):
    api = (Path(tutor.__file__).parent.parent / "docs" / "API.md").read_text(encoding="utf-8")
    assert f"tutor.{module}" in api
    assert function in api


def _every_command(parser=None, prefix=""):
    """'init', 'child add', 'codes new', ... as the real parser defines them."""
    from tutor.cli import build_parser

    names = []
    for action in (parser or build_parser())._actions:
        if isinstance(getattr(action, "choices", None), dict) and action.dest in ("command", "action"):
            for name, sub in action.choices.items():
                deeper = _every_command(sub, f"{prefix}{name} ")
                names += deeper or [f"{prefix}{name}"]
    return names


@pytest.mark.parametrize("command", _every_command())
def test_cheatsheet_lists_every_command(command):
    sheet = (Path(tutor.__file__).parent.parent / "docs" / "CHEATSHEET.md").read_text(encoding="utf-8")
    assert f"tutor {command}" in sheet


@pytest.mark.parametrize("sheet_name", ["CHEATSHEET_session_admin.md", "CHEATSHEET_dry_run.md"])
def test_every_command_in_the_short_sheets_is_accepted_by_the_parser(sheet_name):
    from tutor.cli import build_parser

    sheet = (Path(tutor.__file__).parent.parent / "docs" / sheet_name).read_text(encoding="utf-8")
    commands = re.findall(r"`tutor ([^`]+)`", sheet)
    assert len(commands) >= 6
    for command in commands:
        argv = command.replace("CHILD", "adam").replace("FILE", "codes.txt").replace("ID", "x").replace("PATH", "p").replace("<code>", "X").split()
        build_parser().parse_args(argv)


BUILTIN_PICTURES = sorted((PACKAGE_DATA / "subjects").glob("*/diagrams/*.html"))


@pytest.mark.parametrize("path", BUILTIN_PICTURES, ids=lambda p: p.name)
def test_prepared_pictures_are_simple_self_contained_and_closable(path):
    import xml.etree.ElementTree as ET

    text = path.read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) < 6000, "keep pictures simple"
    assert "<script" not in text and "http" not in text and "src=" not in text and "href=" not in text
    assert "<title>" in text and "click the x" in text.lower(), "every picture says how to close it"
    ET.fromstring(re.search(r"<svg.*?</svg>", text, re.S).group(0))  # well-formed drawing


def test_every_lesson_in_the_builtin_unit_has_a_short_checked_text_diagram():
    text = (PACKAGE_DATA / "subjects" / "physics" / "units" / "forces.md").read_text(encoding="utf-8")
    blocks = re.findall(r"- \*\*Draw it:\*\*.*?\n  ```\n(.*?)\n  ```", text, re.S)
    assert len(blocks) == 5
    for block in blocks:
        lines = [line[2:] for line in block.split("\n")]
        assert len(lines) <= 12 and max(len(line) for line in lines) <= 60, block


def _every_option_string():
    """Every --flag in every command of the real parser."""
    from tutor.cli import build_parser

    found, pending = set(), [build_parser()]
    while pending:
        parser = pending.pop()
        for action in parser._actions:
            found.update(o for o in action.option_strings if o.startswith("--") and o != "--help")
            pending.extend(getattr(action, "choices", None).values() if hasattr(action, "choices") and isinstance(action.choices, dict) else [])
    return sorted(found)


@pytest.mark.parametrize("flag", _every_option_string())
def test_the_full_cheatsheet_lists_every_command_line_flag(flag):
    sheet = (Path(tutor.__file__).parent.parent / "docs" / "CHEATSHEET.md").read_text(encoding="utf-8")
    assert flag in sheet


def test_the_docs_describe_the_sandbox_contents():
    docs = Path(tutor.__file__).parent.parent / "docs"
    for name in ("workflows.md", "CHEATSHEET.md"):
        assert "diagrams" in (docs / name).read_text(encoding="utf-8"), name


def test_the_tutor_is_told_to_reply_first_and_log_afterwards(sandbox):
    skill = (sandbox / "SKILL.md").read_text(encoding="utf-8")
    assert "send your reply to Adam first, then do the slow work" in skill
    assert "No need to answer this one. It's for you to think about while I save our work." in skill
    assert "never ask about it afterwards, never score it" in skill
    assert "read it before anything else" in skill
    assert "Do this after you have sent your reply, not before" in skill
