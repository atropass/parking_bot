from guardrails.pii_filter import contains_sensitive_data, redact_pii


def test_detects_credit_card():
    text = "My credit card number is 4111-1111-1111-1111"
    assert contains_sensitive_data(text)


def test_redact_replaces_credit_card():
    text = "Card: 4111-1111-1111-1111, thanks."
    redacted = redact_pii(text)
    assert "4111" not in redacted
    assert "<CREDIT_CARD>" in redacted
