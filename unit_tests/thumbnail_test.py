import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main import FarmingRobot  # noqa: E402


@pytest.fixture
def robot():
    return FarmingRobot()


def test_add_profile_img_finds_thumbnail(robot):
    result = robot.add_profile_img("tomato")
    assert result is not None
    assert Path(result).stem == "tomato"


def test_add_profile_img_handles_multi_word_names(robot):
    result = robot.add_profile_img("Bell Pepper")  # file is bell_pepper.svg
    assert result is not None
    assert Path(result).stem == "bell_pepper"

#passes
def test_add_profile_img_returns_none_for_unknown_plant(robot):
    assert robot.add_profile_img("not_a_real_plant") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])