"""Tests for tutor.subjects: the built-in physics pack, front matter, lesson parsing and every failure mode."""
import pytest

from tutor.errors import SubjectError
from tutor.subjects import available_subjects, load_subject, split_front_matter

GOOD_UNIT = (
    '+++\nid = "u1"\ntitle = "Unit One"\n+++\n# Unit\n\n'
    "## Lesson 0 — Intro\n\n**Goal:** ${name} knows A.\n\n"
    "## Lesson 1 — Next\n\n**Goal:** ${name} knows B.\n"
)
GOOD_SUBJECT = (
    'title = "toy math"\nscope_in = "Toy math"\nadjacent_examples = "x"\n'
    'greeting = "Hi"\nbridge_map = ["a → b"]\nunits = ["u1"]\n'
)


def make_subject(home, subject_id="toy", subject_toml=GOOD_SUBJECT, units=None):
    units = {"u1": GOOD_UNIT} if units is None else units
    folder = home.subjects_dir / subject_id
    (folder / "units").mkdir(parents=True)
    (folder / "subject.toml").write_text(subject_toml, encoding="utf-8")
    for unit_id, text in units.items():
        (folder / "units" / f"{unit_id}.md").write_text(text, encoding="utf-8")


def test_builtin_physics_pack_loads(physics):
    assert physics.subject_id == "physics"
    assert [lesson.lesson_id for lesson in physics.lessons] == [f"forces.{n}" for n in range(5)]
    assert all(lesson.goal and lesson.title for lesson in physics.lessons)
    assert physics.greeting.startswith("Hello! I'm Claude")
    assert physics.roadmap and physics.bridge_map


def test_remaining_lessons_follow_teaching_order(physics):
    assert [l.lesson_id for l in physics.remaining([])][:2] == ["forces.0", "forces.1"]
    assert [l.lesson_id for l in physics.remaining({"forces.0", "forces.2"})] == ["forces.1", "forces.3", "forces.4"]
    assert physics.remaining({l.lesson_id for l in physics.lessons}) == ()


def test_lesson_lookup(physics):
    assert physics.lesson("forces.3").title.startswith("Newton's Second Law")
    with pytest.raises(SubjectError, match="Unknown lesson id"):
        physics.lesson("forces.99")


def test_available_subjects_lists_builtin_and_home_packs(home):
    make_subject(home)
    assert available_subjects(home) == ["physics", "toy"]


def test_home_pack_is_found_and_parsed(home):
    make_subject(home)
    subject = load_subject(home, "toy")
    assert [l.lesson_id for l in subject.lessons] == ["u1.0", "u1.1"]
    assert subject.lessons[0].goal == "${name} knows A."  # placeholders stay raw until rendering


def test_home_pack_overrides_builtin_of_the_same_name(home):
    make_subject(home, "physics", GOOD_SUBJECT.replace("toy math", "my physics"))
    assert load_subject(home, "physics").title == "my physics"


def test_unknown_subject_lists_available(home):
    with pytest.raises(SubjectError, match=r"No subject 'chem'.*physics"):
        load_subject(home, "chem")


def test_front_matter_split_and_crlf():
    meta, body = split_front_matter('+++\r\nid = "x"\r\n+++\r\nbody\r\n', "f")
    assert meta == {"id": "x"} and body == "body\n"


def test_empty_front_matter_is_allowed():
    assert split_front_matter("+++\n+++\nbody", "f") == ({}, "body")


@pytest.mark.parametrize("text", ["no front matter", '+++\nid = "x"\nnever closed', ""])
def test_missing_or_unclosed_front_matter_fails(text):
    with pytest.raises(SubjectError, match="front matter"):
        split_front_matter(text, "f")


def test_invalid_front_matter_toml_fails():
    with pytest.raises(SubjectError, match="not valid TOML"):
        split_front_matter("+++\nid = \n+++\nbody", "f")


@pytest.mark.parametrize("subject_toml, message", [
    (GOOD_SUBJECT + 'flavor = "x"\n', "unknown fields"),
    (GOOD_SUBJECT.replace('title = "toy math"\n', ""), "'title'"),
    (GOOD_SUBJECT.replace('bridge_map = ["a → b"]', "bridge_map = []"), "bridge_map"),
    (GOOD_SUBJECT.replace('units = ["u1"]', "units = []"), "units"),
    (GOOD_SUBJECT.replace('units = ["u1"]', 'units = ["u1", "u1"]'), "duplicate unit"),
    (GOOD_SUBJECT.replace('units = ["u1"]', "units = [1]"), "units"),
    (GOOD_SUBJECT + "roadmap = [1]\n", "roadmap"),
    ("title = \n", "not valid TOML"),
])
def test_bad_subject_toml_fails(home, subject_toml, message):
    make_subject(home, subject_toml=subject_toml)
    with pytest.raises(SubjectError, match=message):
        load_subject(home, "toy")


def test_unit_file_missing(home):
    make_subject(home, units={})
    with pytest.raises(SubjectError, match="does not exist"):
        load_subject(home, "toy")


def test_unit_id_must_match_file_name(home):
    make_subject(home, units={"u1": GOOD_UNIT.replace('id = "u1"', 'id = "other"')})
    with pytest.raises(SubjectError, match="expected 'u1'"):
        load_subject(home, "toy")


def test_unit_without_lessons_fails(home):
    make_subject(home, units={"u1": '+++\nid = "u1"\ntitle = "T"\n+++\njust text\n'})
    with pytest.raises(SubjectError, match="no '## Lesson"):
        load_subject(home, "toy")


def test_duplicate_lesson_numbers_fail(home):
    make_subject(home, units={"u1": GOOD_UNIT.replace("Lesson 1", "Lesson 0")})
    with pytest.raises(SubjectError, match="appears twice"):
        load_subject(home, "toy")


def test_lesson_without_goal_fails(home):
    make_subject(home, units={"u1": GOOD_UNIT.replace("**Goal:** ${name} knows B.", "no goal here")})
    with pytest.raises(SubjectError, match="Lesson 1 has no '\\*\\*Goal"):
        load_subject(home, "toy")


def test_goal_must_belong_to_its_own_lesson(home):
    text = GOOD_UNIT.replace("**Goal:** ${name} knows A.\n\n", "")  # Lesson 0 loses its goal
    make_subject(home, units={"u1": text})
    with pytest.raises(SubjectError, match="Lesson 0 has no"):
        load_subject(home, "toy")


def test_placeholders_in_titles_fail(home):
    make_subject(home, units={"u1": GOOD_UNIT.replace("Lesson 0 — Intro", "Lesson 0 — ${name}")})
    with pytest.raises(SubjectError, match="titles cannot contain placeholders"):
        load_subject(home, "toy")


def test_the_unit_names_vectors_in_lesson_one(physics):
    """Lesson 1 introduces the word 'vector' with its definition, and its goal says so."""
    from tutor.paths import PACKAGE_DATA

    text = (PACKAGE_DATA / "subjects" / "physics" / "units" / "forces.md").read_text(encoding="utf-8")
    assert "vector" in physics.lesson("forces.1").goal
    assert "**vector**" in text.split("## Lesson 1")[1].split("## Lesson 2")[0]


PICTURE_UNIT = GOOD_UNIT.replace("**Goal:** ${name} knows A.\n", "**Goal:** ${name} knows A.\n- **Picture:** sketch  (optional)\n")


def test_a_named_picture_is_resolved_to_the_packs_file(home):
    make_subject(home, units={"u1": PICTURE_UNIT})
    picture = home.subjects_dir / "toy" / "diagrams" / "sketch.html"
    picture.parent.mkdir()
    picture.write_text("<svg></svg>", encoding="utf-8")
    assert load_subject(home, "toy").pictures == (picture,)


def test_a_missing_picture_is_a_loud_error(home):
    make_subject(home, units={"u1": PICTURE_UNIT})
    with pytest.raises(SubjectError, match="names picture 'sketch' but .*sketch.html does not exist"):
        load_subject(home, "toy")


def test_a_picture_named_twice_is_listed_once(home):
    twice = PICTURE_UNIT + "\n## Lesson 2 — Again\n\n**Goal:** ${name} knows C.\n- **Picture:** sketch\n"
    make_subject(home, units={"u1": twice})
    (home.subjects_dir / "toy" / "diagrams").mkdir()
    (home.subjects_dir / "toy" / "diagrams" / "sketch.html").write_text("<svg></svg>", encoding="utf-8")
    assert len(load_subject(home, "toy").pictures) == 1


def test_units_without_picture_lines_have_none(home):
    make_subject(home)
    assert load_subject(home, "toy").pictures == ()


def test_the_builtin_pack_names_one_picture_per_lesson(physics):
    assert [p.stem for p in physics.pictures] == [
        "velocity_change", "tug_of_war", "balanced_book", "same_push", "skaters"]


THINK_UNIT = GOOD_UNIT.replace("**Goal:** ${name} knows A.\n", "**Goal:** ${name} knows A.\n- **Think about:** Why does a ball stop on grass?\n")


def test_a_think_about_line_is_attached_to_its_lesson(home):
    make_subject(home, units={"u1": THINK_UNIT})
    assert load_subject(home, "toy").lessons[0].think_about == "Why does a ball stop on grass?"


def test_a_lesson_without_a_think_about_line_has_none(home):
    make_subject(home)
    assert load_subject(home, "toy").lessons[0].think_about is None


def test_an_overlong_think_about_line_is_a_loud_error(home):
    make_subject(home, units={"u1": THINK_UNIT.replace("Why does a ball stop on grass?", "x" * 241)})
    with pytest.raises(SubjectError, match="Lesson 0: the 'Think about' line is 241 characters; keep it under 240"):
        load_subject(home, "toy")


def test_every_builtin_physics_lesson_has_a_study_only_think_about(physics):
    assert all(lesson.think_about for lesson in physics.lessons)
