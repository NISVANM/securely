import unittest

from app import app


class PatientApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_returns_ok(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_patients_returns_only_sample_records(self):
        response = self.client.get("/patients")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            [
                {"id": 1, "name": "Test Patient A", "condition": "Hypertension"},
                {"id": 2, "name": "Test Patient B", "condition": "Diabetes"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
