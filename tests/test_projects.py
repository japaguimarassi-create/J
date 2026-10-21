import ast
import json
import pytest

from deta.projects import create_project


def test_browser_game_project_contains_playable_files(tmp_path):
    output = tmp_path / "game"
    result = create_project("browser-game", "Target Arena", output, "A touch-friendly game for mobile.")
    assert set(result["files"]) == {"index.html", "style.css", "game.js", "README.md", "project.json"}
    assert "Começar partida" in (output / "index.html").read_text(encoding="utf-8")
    assert "pointerdown" in (output / "game.js").read_text(encoding="utf-8")
    metadata = json.loads((output / "project.json").read_text(encoding="utf-8"))
    assert metadata["uses_ai_api"] is False
    assert metadata["brief"] == "A touch-friendly game for mobile."


def test_social_app_project_has_local_posts_search_and_comments(tmp_path):
    output = tmp_path / "social"
    create_project("social-app", "Community Space", output)
    app = (output / "app.js").read_text(encoding="utf-8")
    assert "localStorage" in app
    assert "post-form" in app
    assert 'makeButton("Comentar"' in app
    assert "textContent = post.text" in app


def test_python_cli_project_has_valid_python(tmp_path):
    output = tmp_path / "tool"
    create_project("python-cli", "Task Organizer", output)
    source = (output / "main.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "commands.add_parser" in source


def test_project_builder_refuses_to_overwrite_non_empty_output(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        create_project("browser-game", "Game", output)
    assert (output / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_project_builder_rejects_unknown_kind_and_empty_name(tmp_path):
    with pytest.raises(ValueError, match="Unsupported project kind"):
        create_project("unknown", "Thing", tmp_path / "out")
    with pytest.raises(ValueError, match="name"):
        create_project("browser-game", "!!!", tmp_path / "out")
