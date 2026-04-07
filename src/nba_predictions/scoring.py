def calculate_score(pred: str, actual: str, is_playin: bool = False) -> int:
    """Score a prediction against an actual series result.

    Format: "home_wins:away_wins" e.g. "4:2"
    Play-in format: "1:0" (home wins) or "0:1" (away wins)

    Regular series rules:
    - 15 pts if predicted winner matches actual winner
    - +10 if loser's game count is exact (diff == 0)
    - +5  if diff == 1
    - +2  if diff == 2
    - +1  if the away team wins the actual series

    Play-in rules:
    - 5 pts if predicted winner matches actual winner
    """
    pred_home, pred_away = int(pred.split(":")[0]), int(pred.split(":")[1])
    actual_home, actual_away = int(actual.split(":")[0]), int(actual.split(":")[1])

    correct_winner = (pred_home - pred_away) * (actual_home - actual_away) > 0

    if is_playin:
        return 5 if correct_winner else 0

    score = 0
    if correct_winner:
        score += 15

        diff = abs(min(pred_home, pred_away) - min(actual_home, actual_away))
        if diff == 0:
            score += 10
        elif diff == 1:
            score += 5
        elif diff == 2:
            score += 2

        if actual_home - actual_away < 0:
            score += 1

    return score
