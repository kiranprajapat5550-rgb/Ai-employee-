"""Consent-based follow-up runner. Dry-run is the default."""
import argparse, csv, json, os, smtplib, ssl, urllib.error, urllib.request
from email.message import EmailMessage

DEFAULT_LIMIT = 20

def truthy(value):
    return str(value or '').strip().lower() in {'1','true','yes','y','on'}

def load_templates(path):
    with open(path, encoding='utf-8') as f: return json.load(f)

def send_email(row, templates):
    host=os.environ['SMTP_HOST']; port=int(os.getenv('SMTP_PORT','465'))
    username=os.environ['SMTP_USER']; password=os.environ['SMTP_PASSWORD']
    msg=EmailMessage(); msg['Subject']=templates['email']['subject']
    msg['From']=os.getenv('EMAIL_FROM',username); msg['To']=row['email']
    msg.set_content(templates['email']['body'].format(name=row.get('name','').strip() or 'there', sender=templates.get('sender','Team')))
    with smtplib.SMTP_SSL(host,port,context=ssl.create_default_context(),timeout=20) as smtp:
        smtp.login(username,password); smtp.send_message(msg)

def send_whatsapp(row, templates):
    token=os.environ['WHATSAPP_TOKEN']; phone_id=os.environ['WHATSAPP_PHONE_NUMBER_ID']
    payload={'messaging_product':'whatsapp','to':row['phone'],'type':'template','template':{'name':os.getenv('WHATSAPP_TEMPLATE_NAME',templates['whatsapp']['template_name']),'language':{'code':os.getenv('WHATSAPP_LANGUAGE','en')}}}
    req=urllib.request.Request(f'https://graph.facebook.com/v21.0/{phone_id}/messages',data=json.dumps(payload).encode(),headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=20) as response:
            if response.status >= 300: raise RuntimeError(f'WhatsApp API HTTP {response.status}')
    except urllib.error.HTTPError as exc: raise RuntimeError(f'WhatsApp API HTTP {exc.code}') from exc

def run(csv_path, templates_path='templates.json', dry_run=None, send_enabled=None, limit=None):
    dry_run=truthy(os.getenv('DRY_RUN','1')) if dry_run is None else dry_run
    send_enabled=truthy(os.getenv('SEND_ENABLED','false')) if send_enabled is None else send_enabled
    limit=int(limit if limit is not None else os.getenv('DAILY_LIMIT',DEFAULT_LIMIT))
    if limit < 1: raise ValueError('DAILY_LIMIT must be at least 1')
    templates=load_templates(templates_path); processed=sent=skipped=0
    with open(csv_path,newline='',encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if processed >= limit: break
            processed += 1; channels=[]
            if truthy(row.get('consent_email')) and row.get('email','').strip(): channels.append('email')
            if truthy(row.get('consent_whatsapp')) and row.get('phone','').strip(): channels.append('whatsapp')
            if not channels:
                skipped += 1; print(f"SKIP {row.get('name','(unnamed)')}: no channel-specific consent"); continue
            for channel in channels:
                if dry_run or not send_enabled:
                    print(f"DRY-RUN {channel}: {row.get('name','(unnamed)')}"); continue
                if channel == 'email': send_email(row,templates)
                else: send_whatsapp(row,templates)
                sent += 1
    print(f'Processed={processed} Sent={sent} Skipped={skipped} DryRun={dry_run} SendEnabled={send_enabled}')
    return {'processed':processed,'sent':sent,'skipped':skipped}

def main():
    p=argparse.ArgumentParser(description='Consent-based follow-up (dry-run by default)')
    p.add_argument('--csv',default='leads.csv'); p.add_argument('--templates',default='templates.json')
    a=p.parse_args(); run(a.csv,a.templates)

if __name__ == '__main__': main()
