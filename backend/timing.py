"""Server-owned stage deadlines and transparent integer scoring."""
LIMITS = {'easy': 180, 'hard': 420}


def score(weight, elapsed_seconds, limit_seconds, hints, attempt=1):
    """Half base + proportional time bonus; hints -25; retries halve the result."""
    elapsed = max(0, int(elapsed_seconds))
    if elapsed >= limit_seconds:
        return 0
    base = weight * 100
    points = base // 2 + (base * (limit_seconds - elapsed)) // (2 * limit_seconds)
    return max(0, points - hints * 25) // (2 if attempt > 1 else 1)
