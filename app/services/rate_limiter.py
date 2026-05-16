from app.config import settings

def is_rate_limited(user_timestamps: list[float], current_time: float) -> bool:
    """
    Sliding Window Log Rate Limiter.
    Tracks precise timestamps of user actions over a moving time window.
    
    Rule Profile: Max 5 notifications per user per minute.
    """
    WINDOW_SIZE_SECONDS = 60
    MAX_REQUESTS_PER_WINDOW = 5

    # 1. Calculate the starting boundary of the current moving window
    window_start_boundary = current_time - WINDOW_SIZE_SECONDS

    # 2. Evict old timestamps that fall outside the active sliding window.
    # In Redis production, this maps to: ZREMRANGEBYSCORE user_key -inf window_start_boundary
    while user_timestamps and user_timestamps[0] < window_start_boundary:
        user_timestamps.pop(0)

    # 3. Check if the user has exhausted their allocation capacity
    # In Redis production, this maps to: ZCARD user_key
    if len(user_timestamps) >= MAX_REQUESTS_PER_WINDOW:
        return True  # Rate limit exceeded. Request must be rejected.

    return False  # Pass. Safe to proceed with queue dispatch.