# app/utils.py

import re
import csv
from .config import settings
from .logging_config import logger
from typing import Dict, Optional

def normalize_subject(subject: str) -> str:
    """
    Normalizes an email subject to identify a conversation thread.
    Strips common and unforeseen prefix patterns (like 'Re:', '[EXTERNAL]:', etc.) 
    and extra whitespace.
    """
    if not subject:
        return ""
        
    prefix_pattern = r'^((\w+|\[.*?\]):\s*)+'
    normalized = re.sub(prefix_pattern, '', subject, flags=re.IGNORECASE)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def get_prospect_details_by_email(prospect_email: str) -> Optional[Dict[str, str]]:
    """
    Finds a prospect in the CSV file by their email address.

    Args:
        prospect_email: The email address of the prospect to find.

    Returns:
        A dictionary containing the prospect's details if found, otherwise None.
    """
    try:
        with open(settings.PROSPECTS_CSV_PATH, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if row.get("Email") and row["Email"].lower() == prospect_email.lower():
                    logger.info({"message": "Found prospect details in CSV", "email": prospect_email})
                    return row
    except FileNotFoundError:
        logger.error({"message": "Prospects CSV file not found", "path": settings.PROSPECTS_CSV_PATH})
    except Exception as e:
        logger.error({"message": "Error reading prospects CSV", "error": str(e)})
    
    logger.warning({"message": "Prospect details not found in CSV", "email": prospect_email})
    return None
