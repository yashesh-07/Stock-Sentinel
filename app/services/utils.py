def safely_truncate_text(body: str, max_chars: int, suffix: str = "...") -> str:
    """
    Protects downstream SMS budgets by hard-clipping long text alerts
    while cleanly appending a tracking trailing suffix if truncation occurs.
    """
    # Edge case defense: Handle tiny or invalid constraints gracefully
    if max_chars <= len(suffix):
        return body[:max_chars]

    # Rule 1: Content fits safely within limits; return unmodified
    if len(body) <= max_chars:
        return body
        
    # Rule 2: Exceeds limits; trim room for the suffix at the END of the payload
    slice_index = max_chars - len(suffix)
    return body[:slice_index] + suffix


def sanitize_notification_body(title: str, body: str | None) -> str:
    """
    Defensively sanitizes inbound body payloads. 
    Falls back to a structural message template if the text is missing or whitespace-only.
    """
    if body is None:
        return f"[Auto-Generated] Update for alert: {title}"
        
    cleaned_body = body.strip()
    
    if not cleaned_body:
        return f"[Auto-Generated] Update for alert: {title}"
        
    return cleaned_body


def parse_enabled_channels(raw_channels: str | None) -> set[str]:
    """
    Parses comma-separated channel parameters from configuration clusters.
    Normalizes mixed casing and strips hidden padding whitespace.
    """
    if not raw_channels:
        return set()
        
    VALID_CHANNELS = {"EMAIL", "SMS", "PUSH"}
    
    return {
        item.strip().upper() 
        for item in raw_channels.split(",") 
        if item.strip().upper() in VALID_CHANNELS
    }