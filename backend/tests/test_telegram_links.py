import pytest
from app.services.telegram_links import (
    clean_and_validate_bot_username,
    clean_and_validate_start_code,
    build_telegram_deep_link
)

def test_bot_username_valid():
    username, err = clean_and_validate_bot_username("AdPulseBot")
    assert username == "AdPulseBot"
    assert err is None

def test_bot_username_with_at_sign():
    username, err = clean_and_validate_bot_username("@AdPulseBot")
    assert username == "AdPulseBot"
    assert err is None

def test_bot_username_with_whitespace():
    username, err = clean_and_validate_bot_username("   @AdPulse_Bot   \n")
    assert username == "AdPulse_Bot"
    assert err is None

def test_bot_username_with_uppercase():
    username, err = clean_and_validate_bot_username("TEST_My_Bot_123")
    assert username == "TEST_My_Bot_123"
    assert err is None

def test_bot_username_too_short():
    username, err = clean_and_validate_bot_username("bot")
    assert username is None
    assert "от 5 до 32 символов" in err

def test_bot_username_empty():
    username1, err1 = clean_and_validate_bot_username("")
    assert username1 is None
    assert err1 is not None

    username2, err2 = clean_and_validate_bot_username("   ")
    assert username2 is None
    assert err2 is not None

    username3, err3 = clean_and_validate_bot_username(None)
    assert username3 is None
    assert err3 is not None

def test_bot_username_invalid_start_char():
    # Must start with a letter
    username1, err1 = clean_and_validate_bot_username("12345bot")
    assert username1 is None
    assert err1 is not None

    username2, err2 = clean_and_validate_bot_username("_my_bot")
    assert username2 is None
    assert err2 is not None

def test_bot_username_invalid_special_chars():
    username, err = clean_and_validate_bot_username("my-bot-name")
    assert username is None
    assert err is not None

def test_start_code_valid():
    code, err = clean_and_validate_start_code("code_123-abc")
    assert code == "code_123-abc"
    assert err is None

def test_start_code_with_whitespace():
    code, err = clean_and_validate_start_code("  secret_code_42  \n")
    assert code == "secret_code_42"
    assert err is None

def test_start_code_empty_or_none():
    assert clean_and_validate_start_code("")[0] is None
    assert clean_and_validate_start_code("   ")[0] is None
    assert clean_and_validate_start_code(None)[0] is None

def test_start_code_invalid_chars():
    assert clean_and_validate_start_code("bad code with spaces")[0] is None
    assert clean_and_validate_start_code("code$special%")[0] is None

def test_build_telegram_deep_link_personal():
    link = build_telegram_deep_link(" @MyBot123 ", " start_code_99 ", is_group=False)
    assert link == "https://t.me/MyBot123?start=start_code_99"

def test_build_telegram_deep_link_group():
    link = build_telegram_deep_link("@MyBot123", "start_code_99", is_group=True)
    assert link == "https://t.me/MyBot123?startgroup=start_code_99"

def test_build_telegram_deep_link_invalid_inputs():
    # Broken username
    assert build_telegram_deep_link("bot", "code123") is None
    assert build_telegram_deep_link("", "code123") is None
    assert build_telegram_deep_link(None, "code123") is None

    # Broken code
    assert build_telegram_deep_link("MyBot123", "") is None
    assert build_telegram_deep_link("MyBot123", "has space") is None
    assert build_telegram_deep_link("MyBot123", None) is None
