import time
import json
import os
import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

WGFD_URL = "https://wgfapps.wyo.gov/QuotaAvailability/SelectionCriteria.aspx"

# Load watch list
with open("tags.json", "r") as f:
    WATCH_LIST = json.load(f)

# Load alerted cache
ALERTED_FILE = "alerted.json"
if os.path.exists(ALERTED_FILE):
    with open(ALERTED_FILE, "r") as f:
        ALERTED = set(json.load(f))
else:
    ALERTED = set()

# Twilio setup
client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))


def send_text(message):
    client.messages.create(
        body=message,
        from_=os.getenv("TWILIO_FROM"),
        to=os.getenv("TWILIO_TO")
    )


def save_alerted():
    with open(ALERTED_FILE, "w") as f:
        json.dump(list(ALERTED), f)


def build_key(tag):
    return f"{tag['species']}-{tag['area']}-Type{tag['type']}"


def check_wgfd():
    print("Checking WGFD...")

    session = requests.Session()
    response = session.get(WGFD_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    # grab hidden ASP.NET fields
    viewstate = soup.find("input", {"name": "__VIEWSTATE"})
    eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})

    data = {
        "__VIEWSTATE": viewstate["value"] if viewstate else "",
        "__EVENTVALIDATION": eventvalidation["value"] if eventvalidation else "",
        "ctl00$MainContent$btnSubmit": "Search"
    }

    # Submit form (basic post-back)
    post = session.post(WGFD_URL, data=data)
    results = BeautifulSoup(post.text, "html.parser").get_text(" ")

    for tag in WATCH_LIST:
        key = build_key(tag)

        if key in ALERTED:
            continue

        search_str = f"{tag['species']} {tag['area']} {tag['type']}"

        if search_str in results:
            msg = f"🚨 WGFD ALERT: {tag['species']} Area {tag['area']} Type {tag['type']} AVAILABLE"
            print(msg)

            send_text(msg)

            ALERTED.add(key)
            save_alerted()


if __name__ == "__main__":
    while True:
        try:
            check_wgfd()
        except Exception as e:
            print("Error:", e)

        time.sleep(90)  # check every 90 seconds