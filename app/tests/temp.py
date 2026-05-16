def extract_unrecoverable_failures(logs: list[dict]) -> list[dict]:
    # Set standard maximum thresholds as clean internal variables
    MAX_RETRY_LIMIT = 3
    
    # List comprehension with protective .get() fallbacks to prevent KeyErrors
    return [
        log for log in logs 
        if log.get("status") == "FAILED" and log.get("retry_count", 0) >= MAX_RETRY_LIMIT
    ]



def is_rate_limited(sent_timestamps: list[float], current_time: float) -> bool:
    # 1. Define constants inside or pull from config
    WINDOW_SIZE = 60  # seconds
    MAX_REQUESTS = 5
    
    threshold_time = current_time - WINDOW_SIZE
    
    # 2. Optimization: Iterate backwards 
    # Because the most recent timestamps are at the end of the list.
    count = 0
    for i in range(len(sent_timestamps) - 1, -1, -1):
        if sent_timestamps[i] > threshold_time:
            count += 1
            if count >= MAX_REQUESTS:
                return True # Fail-fast: Stop the loop immediately
        else:
            # Since the list is sorted, if this one is older than 60s,
            # all previous ones are also older. We can stop entirely.
            break
            
    return False


def safely_truncate_text(body: str, max_chars: int, suffix: str = "...") -> str:
    # Edge case defense: If max_chars is smaller than the suffix itself, 
    # we can't cleanly append it. Just return the hard sliced body.
    if max_chars <= len(suffix):
        return body[:max_chars]

    # Rule 1: If the body already fits within constraints, return it untouched.
    if len(body) <= max_chars:
        return body
        
    # Rule 2: If it exceeds constraints, slice the body down to leave room 
    # for the suffix at the END of the string.
    slice_index = max_chars - len(suffix)
    return body[:slice_index] + suffix


def determine_queue_priority(channel: str, is_critical: bool = False) -> int:
    if is_critical:
        return 1
    if channel == "PUSH":
        return 2
    if channel == "SMS":
        return 3
    if channel == "EMAIL":
        return 4
    raise ValueError("Invalid channel type")


def sanitize_notification_body(title: str, body: str | None) -> str:
    # 1. Handle the None edge-case immediately
    if body is None:
        return f"[Auto-Generated] Update for alert: {title}"
        
    # 2. Sanitize whitespace early
    cleaned_body = body.strip()
    
    # 3. If the string is empty after stripping, fall back to template
    if not cleaned_body:
        return f"[Auto-Generated] Update for alert: {title}"
        
    return cleaned_body



def classify_provider_error(error_msg: str | None) -> str:
    # 1. Immediate fallback check for missing data strings
    if not error_msg:  # Catches both None and empty string "" smoothly
        return "UNKNOWN_PROVIDER_ERROR"
    
    # 2. Normalize the casing for robust pattern analysis
    normalized_msg = error_msg.lower()
    
    # 3. Pattern classification tree matching corporate contract keys
    if "timeout" in normalized_msg or "gateway" in normalized_msg:
        return "NETWORK_TIMEOUT"
        
    if "auth" in normalized_msg or "credential" in normalized_msg or "key" in normalized_msg:
        return "AUTH_FAILURE"
        
    # Retaining your excellent extended telemetry buckets:
    if "rate limit" in normalized_msg or "too many requests" in normalized_msg:
        return "RATE_LIMIT_EXCEEDED"
        
    if "server error" in normalized_msg or "500" in normalized_msg or "503" in normalized_msg:
        return "PROVIDER_SERVER_ERROR"
        
    # 4. Global default string catcher
    return "UNKNOWN_PROVIDER_ERROR"


def parse_enabled_channels(raw_channels: str | None) -> set[str]:
    # 1. Catch None or empty strings immediately
    if not raw_channels:
        return set()
        
    # 2. Strict architectural whitelist boundary
    VALID_CHANNELS = {"EMAIL", "SMS", "PUSH"}
    
    # 3. Clean, split, and normalize each individual item dynamically
    # Running item.strip() inside the loop ensures spaces around inner commas are handled
    return {
        item.strip().upper() 
        for item in raw_channels.split(",") 
        if item.strip().upper() in VALID_CHANNELS
    }

