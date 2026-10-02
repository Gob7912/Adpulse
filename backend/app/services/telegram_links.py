import logging
import re

logger = logging.getLogger("adpulse.telegram_links")

# Telegram Bot username requirements:
# 5-32 characters, letters, digits, underscores, must start with a letter
USERNAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")

# Start parameter requirements:
# 1-64 characters, letters, digits, underscores, hyphens
START_CODE_REGEX = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

def clean_and_validate_bot_username(raw_username: str | None) -> tuple[str | None, str | None]:
    """
    Cleans and validates a Telegram bot username:
    - Strips whitespace and leading '@'
    - Validates against ^[A-Za-z][A-Za-z0-9_]{4,31}$
    Returns (cleaned_username, error_message).
    """
    if not raw_username:
        return None, "Имя бота Telegram не настроено."
    
    cleaned = raw_username.strip()
    if cleaned.startswith("@"):
        cleaned = cleaned[1:].strip()
        
    if not cleaned:
        return None, "Имя бота Telegram пустое."

    if not USERNAME_REGEX.match(cleaned):
        return None, (
            f"Некорректный username бота '{cleaned}'. "
            "Имя должно начинаться с буквы и содержать от 5 до 32 символов (A-Z, a-z, 0-9, _)."
        )

    return cleaned, None

def clean_and_validate_start_code(raw_code: str | None) -> tuple[str | None, str | None]:
    """
    Cleans and validates a Telegram start parameter code:
    - Strips whitespace
    - Validates against ^[A-Za-z0-9_-]{1,64}$
    Returns (cleaned_code, error_message).
    """
    if not raw_code:
        return None, "Код привязки отсутствует."

    cleaned = raw_code.strip()
    if not START_CODE_REGEX.match(cleaned):
        return None, (
            f"Некорректный код привязки '{cleaned}'. "
            "Код должен содержать от 1 до 64 символов (A-Z, a-z, 0-9, _, -)."
        )

    return cleaned, None

def build_telegram_deep_link(
    bot_username: str | None,
    start_code: str | None,
    is_group: bool = False
) -> str | None:
    """
    Builds the deep-link URL in ONE helper function:
    1. Strips whitespace and a leading '@' from the username.
    2. Validates username against ^[A-Za-z][A-Za-z0-9_]{4,31}$.
    3. Validates start code against ^[A-Za-z0-9_-]{1,64}$.
    4. Returns https://t.me/<username>?start=<code> or https://t.me/<username>?startgroup=<code>
    5. Returns None if either is invalid or missing.
    """
    clean_user, _ = clean_and_validate_bot_username(bot_username)
    if not clean_user:
        return None

    clean_code, _ = clean_and_validate_start_code(start_code)
    if not clean_code:
        return None

    param = "startgroup" if is_group else "start"
    return f"https://t.me/{clean_user}?{param}={clean_code}"
