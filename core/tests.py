from django.test import SimpleTestCase
from django.urls import reverse


class HealthcheckTests(SimpleTestCase):
    def test_healthcheck_responde_sem_dependencias_externas(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        self.assertEqual(response["Content-Type"], "text/plain")
