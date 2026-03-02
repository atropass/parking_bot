from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_analyzer = None
_anonymizer = None

SENSITIVE_ENTITIES = [
    "CREDIT_CARD",
    "CRYPTO",
    "IBAN_CODE",
    "IP_ADDRESS",
    "MEDICAL_LICENSE",
    "US_SSN",
    "US_BANK_NUMBER",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
]


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
    return _analyzer


def _get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


def detect_pii(text: str) -> list:
    analyzer = _get_analyzer()
    results = analyzer.analyze(
        text=text,
        entities=SENSITIVE_ENTITIES,
        language="en",
    )
    return results


def redact_pii(text: str) -> str:
    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()

    results = analyzer.analyze(
        text=text,
        entities=SENSITIVE_ENTITIES,
        language="en",
    )

    if not results:
        return text

    anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymized.text


def contains_sensitive_data(text: str) -> bool:
    results = detect_pii(text)
    return len(results) > 0
