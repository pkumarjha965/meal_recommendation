import os

from twilio.rest import Client
import dotenv

dotenv.load_dotenv()



# Your Twilio account SID and Auth Token
account_sid = os.getenv('account_sid')
auth_token = os.getenv('auth_token')
client = Client(account_sid, auth_token)
SENDER_DETAILS_FILE = "/opt/airflow/data/twilio_number.txt"


# Function to send SMS
def send_sms(to_number, message_body):
    try:
        # read the Twilio phone number from the text file TEXT_FILE containing the phone number:[phone_number]
        from_number = open(SENDER_DETAILS_FILE).read().splitlines()[0]
        message = client.messages.create(
            body=message_body,
            from_=from_number,  # Your Twilio phone number
            to=to_number
        )

        print(f"SMS sent to {to_number} with message: {message_body}")
    except Exception as e:
        print(f"Error sending SMS: {e}")


def get_template_msg(items):
    template_msg = "\nToday's menu is: \n {menu_items} \n Enjoy your meal!"
    msg = template_msg.replace("{menu_items}", items)
    return msg
