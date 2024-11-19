import smtplib
from email.mime.text import MIMEText

def send_test_email():
    msg = MIMEText('This is a test email.')
    msg['Subject'] = 'Test Email'
    msg['From'] = 'ai@imaginationplanet.com'
    msg['To'] = 'junkai.xue@gmail.com'

    try:
        with smtplib.SMTP('localhost', 1025) as server:
            server.sendmail('ai@imaginationplanet.com', ['junkai.xue@gmail.com'], msg.as_string())
            print('Email sent successfully.')
    except Exception as e:
        print(f'Failed to send email: {e}')

if __name__ == '__main__':
    send_test_email()
