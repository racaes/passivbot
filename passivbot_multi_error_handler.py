import subprocess
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json


with open("/home/tdb/config_to_live/mail_config.json", "r") as f:
    mail_config = json.load(f)

# Gmail configuration
GMAIL_ADDRESS = mail_config["GMAIL_ADDRESS"]
GMAIL_PASSWORD = mail_config["GMAIL_PASSWORD"]
TO_EMAIL_ADDRESS = mail_config["TO_EMAIL_ADDRESS"]

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = TO_EMAIL_ADDRESS
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(GMAIL_ADDRESS, TO_EMAIL_ADDRESS, text)
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")

def run_script():
    script_path = '/home/tdb/git/passivbot/passivbot_multi.py'
    config_path = '/home/tdb/config_to_live/multi_v04b_cherry_corr_live.hjson'
    working_directory = '/home/tdb/git/passivbot/'

    while True:
        try:
            subprocess.run(['python', script_path, config_path], check=True, cwd=working_directory)
        except subprocess.CalledProcessError as e:
            print(f"Script failed with error: {e}")
            send_email("Script Error", f"The script failed with error: {e}")
            time.sleep(60)  # Wait for 1 minute before restarting
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            send_email("Unexpected Error", f"An unexpected error occurred: {e}")
            time.sleep(60)  # Wait for 1 minute before restarting

if __name__ == "__main__":
    run_script()