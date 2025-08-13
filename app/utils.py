# app/utils.py (Updated)

import re

def normalize_subject(subject: str) -> str:
    """
    Normalizes an email subject to identify a conversation thread.
    Strips common and unforeseen prefix patterns (like 'Re:', '[EXTERNAL]:', etc.) 
    and extra whitespace. This handles repeated prefixes as well.
    """
    if not subject:
        return ""
        
    # This regex looks for one or more occurrences of a prefix pattern at the start of the string.
    # A prefix pattern is defined as:
    #   - A word (e.g., "Re", "Fwd") followed by a colon.
    #   - OR, any text inside square brackets (e.g., "[EXTERNAL]") followed by a colon.
    #   - Followed by any amount of whitespace.
    prefix_pattern = r'^((\w+|\[.*?\]):\s*)+'
    
    normalized = re.sub(prefix_pattern, '', subject, flags=re.IGNORECASE)
    
    # Collapse any remaining multiple whitespace characters into a single space and strip ends.
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized