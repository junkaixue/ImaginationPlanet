import yagmail
import datetime

email_info_path = 'email.info'


def send_email(content):
    email_info = {}
    for line in open(email_info_path, 'r').readlines():
        data = line.strip().split('=')
        email_info[data[0]] = data[1]

    # Initialize the SMTP client
    yag = yagmail.SMTP(email_info["from_email"], email_info["app_password"])

    # Define the recipient, subject, and content
    subject = '[' +  str(datetime.date) + '] Imagination Planet Complete!'

    # Send the email
    yag.send(to=email_info["to_email"], subject=subject, contents=content)
    print('Email successfully sent!')


if __name__ == '__main__':
    send_email("Test")
