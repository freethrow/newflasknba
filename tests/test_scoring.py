import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nba_predictions.scoring import calculate_score


@pytest.mark.parametrize("pred,actual,expected", [
    ("4:2", "4:2", 25),
    ("4:2", "4:3", 20),
    ("4:2", "4:1", 20),
    ("4:2", "4:0", 17),
    ("4:3", "4:0", 15),
    ("4:2", "2:4", 0),
    ("2:4", "4:2", 0),
    ("2:4", "2:4", 26),
    ("2:4", "1:4", 21),
    ("0:4", "0:4", 26),
    ("4:0", "4:0", 25),
])
def test_calculate_score(pred, actual, expected):
    assert calculate_score(pred, actual) == expected


@pytest.mark.parametrize("pred,actual,expected", [
    # correct winner (home) — 5 pts
    ("1:0", "1:0", 5),
    # correct winner (away) — 5 pts
    ("0:1", "0:1", 5),
    # wrong winner — 0 pts
    ("1:0", "0:1", 0),
    ("0:1", "1:0", 0),
])
def test_calculate_score_playin(pred, actual, expected):
    assert calculate_score(pred, actual, is_playin=True) == expected
