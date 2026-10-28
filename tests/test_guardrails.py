import unittest
from app.application.guardrails import GuardrailsService, AIRefusalError, GuardrailValidationError
from app.domain.models import NotificationType


class TestGuardrailsService(unittest.TestCase):
    def test_canonical_json(self):
        raw = '{"to": "user@test.com", "message": "Hola mundo", "type": "email"}'
        result = GuardrailsService.process_and_validate(raw)
        self.assertEqual(result.to, "user@test.com")
        self.assertEqual(result.message, "Hola mundo")
        self.assertEqual(result.type, NotificationType.EMAIL)

    def test_synonyms_mapping(self):
        raw = '{"Recipient": "600123456", "body": "Codigo 1234", "channel": "sms"}'
        result = GuardrailsService.process_and_validate(raw)
        self.assertEqual(result.to, "600123456")
        self.assertEqual(result.message, "Codigo 1234")
        self.assertEqual(result.type, NotificationType.SMS)

    def test_markdown_code_blocks(self):
        raw = """He extraído la información correctamente:
```json
{"to": "feda@test.com", "message": "Tu pedido ha salido", "type": "email"}
```"""
        result = GuardrailsService.process_and_validate(raw)
        self.assertEqual(result.to, "feda@test.com")
        self.assertEqual(result.message, "Tu pedido ha salido")
        self.assertEqual(result.type, NotificationType.EMAIL)

    def test_conversational_embedded_json(self):
        raw = 'Claro, el destino es test@test.com y enviaré hola por email. En formato JSON: {"to": "test@test.com", "message": "hola", "type": "email"}'
        result = GuardrailsService.process_and_validate(raw)
        self.assertEqual(result.to, "test@test.com")
        self.assertEqual(result.message, "hola")

    def test_single_quotes_json(self):
        raw = "{'to': 'user@example.com', 'message': 'recordatorio', 'type': 'email'}"
        result = GuardrailsService.process_and_validate(raw)
        self.assertEqual(result.to, "user@example.com")
        self.assertEqual(result.message, "recordatorio")

    def test_unquoted_keys_json(self):
        raw = '{to: "611222333", message: "cita confirmada", type: "sms"}'
        result = GuardrailsService.process_and_validate(raw)
        self.assertEqual(result.to, "611222333")
        self.assertEqual(result.message, "cita confirmada")
        self.assertEqual(result.type, NotificationType.SMS)

    def test_truncated_json(self):
        raw = '{"to": "truncated@test.com", "message": "msg", "type": "email" ...'
        result = GuardrailsService.process_and_validate(raw)
        self.assertEqual(result.to, "truncated@test.com")
        self.assertEqual(result.type, NotificationType.EMAIL)

    def test_missing_type_infer_from_email(self):
        raw = '{"to": "juan@test.com", "message": "saludos"}'
        result = GuardrailsService.process_and_validate(raw)
        self.assertEqual(result.type, NotificationType.EMAIL)

    def test_missing_to_rescue_from_user_input(self):
        raw = '{"message": "tu pedido llega manana", "type": "email"}'
        user_prompt = "Enviar email a carlos@domain.com avisando que tu pedido llega manana"
        result = GuardrailsService.process_and_validate(raw, user_input=user_prompt)
        self.assertEqual(result.to, "carlos@domain.com")
        self.assertEqual(result.type, NotificationType.EMAIL)

    def test_refusal_raises_error(self):
        raw = "Lo siento, como IA no tengo permitido procesar datos de contacto personales."
        with self.assertRaises(AIRefusalError):
            GuardrailsService.process_and_validate(raw)


if __name__ == "__main__":
    unittest.main()
