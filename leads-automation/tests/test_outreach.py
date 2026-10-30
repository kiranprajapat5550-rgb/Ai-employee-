import csv, json, tempfile, unittest
from pathlib import Path
from outreach import run

class OutreachTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.csv=self.root/'leads.csv'; self.templates=self.root/'templates.json'
        self.templates.write_text(json.dumps({'sender':'Test Team','email':{'subject':'Test','body':'Hello {name}, from {sender}'},'whatsapp':{'template_name':'followup_intro'}}),encoding='utf-8')
    def tearDown(self): self.tmp.cleanup()
    def write(self, consent_email='false', consent_whatsapp='false', email='a@example.com', phone=''):
        with self.csv.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['name','email','phone','consent_email','consent_whatsapp']); w.writeheader(); w.writerow({'name':'A','email':email,'phone':phone,'consent_email':consent_email,'consent_whatsapp':consent_whatsapp})
    def test_no_consent_skips(self):
        self.write(); self.assertEqual(run(str(self.csv),str(self.templates),dry_run=True,send_enabled=False),{'processed':1,'sent':0,'skipped':1})
    def test_consent_dry_run_never_sends(self):
        self.write(consent_email='true'); self.assertEqual(run(str(self.csv),str(self.templates),dry_run=True,send_enabled=True),{'processed':1,'sent':0,'skipped':0})

if __name__ == '__main__': unittest.main()
