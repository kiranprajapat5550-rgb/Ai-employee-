import csv, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

from outreach import run


class OutreachTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.csv = self.root / "leads.csv"
        self.templates = self.root / "templates.json"
        self.templates.write_text(
            json.dumps({
                "sender": "Test Team",
                "email": {"subject": "Test", "body": "Hello {name}, from {sender}"},
                "whatsapp": {"template_name": "followup_intro"},
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, consent_email="false", consent_whatsapp="false",
              email="a@example.com", phone=""):
        with self.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "email", "phone",
                            "consent_email", "consent_whatsapp"],
            )
            writer.writeheader()
            writer.writerow({
                "name": "A",
                "email": email,
                "phone": phone,
                "consent_email": consent_email,
                "consent_whatsapp": consent_whatsapp,
            })

    def test_no_consent_skips(self):
        self.write()
        result = run(str(self.csv), str(self.templates),
                     dry_run=True, send_enabled=False)
        self.assertEqual(result, {"processed": 1, "sent": 0, "skipped": 1})

    def test_consent_dry_run_never_sends(self):
        self.write(consent_email="true")
        with patch("outreach.send_email") as send_email:
            result = run(str(self.csv), str(self.templates),
                         dry_run=True, send_enabled=True)
        self.assertEqual(result, {"processed": 1, "sent": 0, "skipped": 0})
        send_email.assert_not_called()

    def test_send_disabled_never_sends(self):
        self.write(consent_email="true")
        with patch("outreach.send_email") as send_email:
            result = run(str(self.csv), str(self.templates),
                         dry_run=False, send_enabled=False)
        self.assertEqual(result, {"processed": 1, "sent": 0, "skipped": 0})
        send_email.assert_not_called()


if __name__ == "__main__":
    unittest.main()
