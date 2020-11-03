#!/usr/bin/python3

import json
import requests
import time
import urllib
import config
from googletrans import Translator
import mysql.connector
from similarity import find_most_similar
from corpus import CORPUS


faqdb = mysql.connector.connect(
  host="soli-db.ciksb20swlbf.ap-south-1.rds.amazonaws.com",
  user="faquser",
  password="Faq@123",
  database ="db_faqs"
)

print(faqdb)
cursor = faqdb.cursor() 

TOKEN = "1398831446:AAGxaLjuv4y7ZWCTa5UqDmuEgg5z1CFZxrA"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)

# Confidence of the Bot to give Answers
confidence_score = {
        "min_score": 0.2
    }


# Keyword Matching
GREETING_INPUTS = ["hello", "hi", "greetings", "sup", "what's up","hey"]
THANK_INPUTS = ["thanks", "thank you"]
EXIT_INPUTS = ["bye", "cool", "ok", "great"]


# Generating response
def response(user_response, raw_response, detected_lang, category):
    query = user_response
    answer = find_most_similar(category, query)
    if (answer['score'] > confidence_score['min_score']):
        # set off event asking if the response question is what they were looking for
        print ("\nBest-fit question: %s (Score: %s)\nAnswer: %s\n" % (answer['question'],
                                                                        answer['score'],
                                                                        answer['answer']))
        SoliBot_response = answer['answer']
        return SoliBot_response

    else:
        try:
            #Sending Un-Answered Query to Database
            sql = "INSERT INTO unanswered (un_que_lang, un_que_cat, un_que_en) VALUES (%s, %s, %s)"
            val = (raw_response, detected_lang, user_response)
            cursor.execute(sql, val)
            faqdb.commit()
            print(cursor.rowcount, "Un-Answered Question pushed to FAQ Database")
            SoliBot_response = "I'm sorry i didn't catch that! \nCould you please rephrase that query?"
        except:
            SoliBot_response = "I'm sorry i didn't catch that! \nCould you please rephrase that query?"
        return SoliBot_response


def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates"
    if offset:
        url += "?offset={}".format(offset)
    js = get_json_from_url(url)
    return js


def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def echo_all(updates):
    for update in updates["result"]:
        try:
            raw_response = update["message"]["text"]
            raw_response=raw_response.lower()
            category = "General"
            try:
                translator = Translator(service_urls=['translate.google.com'])
                transx = translator.translate(raw_response, dest='en')
                detected_lang = transx.src
                user_response = transx.text
            except:
                user_response = raw_response
                detected_lang = "en"
            print(user_response)
            if user_response in GREETING_INPUTS:
                resp = "Hey there! I'm SoliBot! \nI'm here to help you with your queries. \nPlease ask me your question... "
            elif user_response in THANK_INPUTS:
                resp = "You are Welcome :) \nPlease come back for any more queries..."
            elif user_response in EXIT_INPUTS:
                resp = "See you Around! \nPlease come back for any more queries :)"
            else:
                resp = response(user_response, raw_response, detected_lang, category)
            transx_final = translator.translate(resp, dest=detected_lang)
            final_response = transx_final.text

            chat = update["message"]["chat"]["id"]
            send_message(final_response, chat)
        except:
            final_response = "Invalid Message! I can only understand text. \nCould you please ask me your query as a text?"
            chat = update["message"]["chat"]["id"]
            send_message(final_response, chat)


def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)


def send_message(text, chat_id):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}".format(text, chat_id)
    get_url(url)


def main():
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            echo_all(updates)
        time.sleep(0.5)


if __name__ == '__main__':
    main()