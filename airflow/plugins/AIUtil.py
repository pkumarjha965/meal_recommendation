import os
from time import sleep
import dotenv
import requests

dotenv.load_dotenv()

HF_token = os.getenv('HF_API_KEY')


API_URL = "https://api-inference.huggingface.co/models/facebook/mbart-large-50-many-to-many-mmt"
headers = {"Authorization": f"Bearer {HF_token}"}
RE_ATTEMPTS = 5


def translate(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()


def translate_to_hindi(msg):
    # re-try 5 times in case of failure
    for i in range(RE_ATTEMPTS):

        try:
            response_data = translate({
            "inputs": msg,  # The text you want to translate
            "parameters": {
                "src_lang": "en_XX",  # Source language: English
                "tgt_lang": "hi_IN"  # Target language: Hindi
            }
            })
            if response_data:
                # parse Json data
                # if response data is a list, get the first element
                response_data_parsed = response_data[0] if isinstance(response_data, list) else response_data
                if response_data_parsed.get('error') is not None:
                    print(f"Error translating text: {response_data_parsed['error']}")
                    raise Exception(response_data_parsed['error'])
                else:
                    break
        except Exception as e:
            print(f"Error translating text: {e}")
            #introduce a delay of 5 seconds before retrying
            sleep(5)
            continue

    response_data = translate({
        "inputs": msg,  # The text you want to translate
        "parameters": {
            "src_lang": "en_XX",  # Source language: English
            "tgt_lang": "hi_IN"  # Target language: Hindi
        }
    })
    print(response_data)
    translated_text = response_data[0]['translation_text']
    print(f"Translated text: {translated_text}")
    return translated_text


# translate_to_hindi("How can we pull this off ?")


