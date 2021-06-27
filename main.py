"""
| *@created on:* 08/05/21,
| *@author:* Abhishek Sharma,
| *@version:* v0.0.1
|
| *Description:* CRON to check for slots every 5 sec and notify if found
|
"""
from datetime import datetime, timedelta
import time
import traceback
import pytz
from cachetools import TTLCache
from skpy import Skype
import requests
import constants
import shelve

# Cache data to avoid sending redundant messages, kill variables after 50 minutes
cache = TTLCache(maxsize=500, ttl=3000)

if constants.skype_notifier:
    sk = Skype(constants.user_id, constants.password)  # connect to Skype

COWIN_URL = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/{0}By{1}?{2}={3}&date={4}"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}


def send_skype_msg(message):
    """
    |   1. Create a skype channel using the recipients provided by user
    |   2. Store the channel id in file and Send Skype message to the channel
    """
    d = shelve.open("./skype_data")
    if "channel_id" in d:
        ch = sk.chats.chat(d["channel_id"])
        ch.sendMsg(message)
    else:
        ch = sk.chats.create(constants.recipients)
        ch.sendMsg(message)
        d["channel_id"] = ch.id


def get_cowin_url(query_date):
    if constants.is_query_by_district:
        return COWIN_URL.format("find", "District", "district_id", constants.dist_code, query_date.strftime("%d-%m-%Y"))
    else:
        return COWIN_URL.format("find", "Pin", "pincode", constants.pincode, query_date.strftime("%d-%m-%Y"))


def get_cowin_url_7_day(query_date):
    if constants.is_query_by_district:
        return COWIN_URL.format("calendar", "District", "district_id", constants.dist_code,
                                query_date.strftime("%d-%m-%Y"))
    else:
        return COWIN_URL.format("calendar", "Pin", "pincode", constants.pincode, query_date.strftime("%d-%m-%Y"))


def validate_and_send_message(dose_1, dose_2, min_age_limit, vaccine, name, pincode, vaccine_date,
                              session_id, cost):
    """
    Get notifications for Dose 1
        Send notifications if dose 1 > 0
    Get notifications for Dose 2
        Send notifications if dose 1 > 0
    Get notifications for Dose 1 & 2
        Send notifications if dose 1 > 0 and dose 2 > 0
    """
    if "DOSE 1" in constants.dosage and dose_1 < 10:
        return
    if "DOSE 2" in constants.dosage and dose_2 < 10:
        return
    if ("DOSE 1" in constants.dosage and "DOSE 2" in constants.dosage) and (dose_1 < 10 and dose_2 < 10):
        return

    if min_age_limit in constants.age_limit and vaccine in constants.vaccine_type:
        message = f"{pincode}, \nAGE {str(min_age_limit)}\n{str(dose_1)}-D1, {str(dose_2)}-D2 slots\n#{vaccine} on {vaccine_date} \n@ {name}({cost})"

        session_msg = session_id + vaccine_date + str(min_age_limit) + vaccine
        if session_msg in cache:
            print("Cached: {}".format(session_msg))
            return
        print(f"-- Slot found --\n{message}\n---")
        try:
            # Broadcast notification from here via Twitter / Skype / Telegram
            if constants.skype_notifier:
                send_skype_msg(message)
        except Exception:
            traceback.print_exc()
        finally:
            cache[session_msg] = session_msg


def get_vaccine_availability_daily(query_date):
    """
    |    *Validations*:
    |          1. Available Capacity should be greater than 5
    |          2. If Age 45+, Check only for Covaxin
    |          3. If Age 18+, Dose 1 should be greater than zero
    """
    try:
        print("Checking for daily availability for {}".format(query_date))
        resp = requests.get(url=get_cowin_url(query_date), headers=HEADERS)
        data = resp.json()
        for session in data['sessions']:
            if session["fee_type"].upper() not in constants.cost:
                continue
            if session["fee_type"] == "Free":
                cost = "Free"
            else:
                cost = str(session["fee"]) + "Rs"

            validate_and_send_message(session['available_capacity_dose1'],
                                      session['available_capacity_dose2'], session["min_age_limit"],
                                      session["vaccine"], session["name"],
                                      str(session["pincode"]), session["date"], session["session_id"], cost)
    except Exception:
        traceback.print_exc()


def get_covaxin_availability_7_day(query_date):
    """
    |    *Validations*:
    |          1. Available Capacity should be greater than 5
    |          2. If Age 45+, Check only for Covaxin
    |          3. If Age 18+, Dose 1 should be greater than zero
    """

    try:
        print("Checking for weekly availability for {}".format(query_date))
        resp = requests.get(url=get_cowin_url_7_day(query_date), headers=HEADERS)
        data = resp.json()
        for center in data['centers']:
            for session in center['sessions']:
                cost = "Free"
                if center["fee_type"].upper() not in constants.cost:
                    break
                if center["fee_type"] != "Free":
                    for v_fee in center["vaccine_fees"]:
                        if session["vaccine"] == v_fee["vaccine"]:
                            cost = str(v_fee["fee"]) + "Rs"
                            break
                validate_and_send_message(session['available_capacity_dose1'],
                                          session['available_capacity_dose2'], session["min_age_limit"],
                                          session["vaccine"], center["name"], str(center["pincode"]),
                                          session["date"], session["session_id"], cost)
    except Exception:
        traceback.print_exc()


"""
|   *Get IST TIME and get slot availability for*
|       1. Today (From 12:00am to 04:00pm, Check every 5 seconds)
|       2. Tomorrow (Check every 5 seconds)    
|       3. Next 7 Days (Check every 10 seconds) 
"""
try:
    while True:
        utc_date_time = datetime.now(pytz.utc)
        ist_date_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        ist_next_date_time = ist_date_time + timedelta(days=1)
        utc_second = int(utc_date_time.strftime('%S'))
        ist_hour = int(ist_date_time.strftime('%H'))
        if ist_hour >= 16:  # After 4pm check slots only for next day
            get_vaccine_availability_daily(ist_next_date_time)
        else:
            # Check slots for today and tomorrow
            get_vaccine_availability_daily(ist_date_time)
            get_vaccine_availability_daily(ist_next_date_time)

        # Check slots for next 7 days
        if utc_second % 10 == 0:
            get_covaxin_availability_7_day(ist_date_time)

        time.sleep(5)
except Exception:
    traceback.print_exc()
