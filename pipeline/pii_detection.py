from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def pii_reduct(text:str) -> dict:
    results = analyzer.analyze(
        text = text ,
        entities = ["CREDIT_CARD","PHONE_NUMBER","EMAIL_ADDRESS"],
        language = 'en'
    )

    if not results:
        return {
            "redacted_text": text,
            "pii_detection": False,
            "entitites_found": []
        }

    anonymized = anonymizer.anonymize(
        text = text,
        analyzer_results = results,
        operators = {"CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CREDIT_CARD]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            }

    )

    return {
        "redacted_text": anonymized.text,
        "pii_reduction": True,
        "entities_found" : [i.entity_type for i in results]

    }

if __name__ == "__main__":
    test = "Hi my name is Kumar, my credit card is 4111111111111111 and my email is kumar@gmail.com"
    result = pii_reduct(test)
    print("Original:", test)
    print("Redacted:", result["redacted_text"])
    print("PII Found:", result["entities_found"])