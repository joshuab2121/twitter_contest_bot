# ---Import needed modules
import time
import threading
import sys
# import requests
# import re
import json
import os.path
# ---Import needed modules from Twitter
from TwitterAPI import TwitterAPI
# ---Import needed modules from Selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
# ---Import needed modules from Beautiful Soup
from bs4 import BeautifulSoup

# Load our configuration from the JSON file.
with open('config.json') as data_file:
    data = json.load(data_file)

# These vars are loaded in from config.
consumer_key = data["consumer-key"]
consumer_secret = data["consumer-secret"]
access_token_key = data["access-token-key"]
access_token_secret = data["access-token-secret"]
search_queries = data["search-queries"]
retweet_update_time = data["retweet-update-time"]
rate_limit_update_time = data["rate-limit-update-time"]
min_ratelimit = data["min-ratelimit"]
min_ratelimit_retweet = data["min-ratelimit-retweet"]
min_ratelimit_search = data["min-ratelimit-search"]
username_or_email = data["username-or-email"]
password = data["password"]
bannedusers = data["banned"]

base_url = 'https://twitter.com/'
query_string = 'search?q='
login_path = 'login'

# ---selenium command
browser = webdriver.Chrome()

# --- TwitterAPI OAuth command
api = TwitterAPI(consumer_key, consumer_secret, access_token_key,
                 access_token_secret)
post_list = list()
ignore_list = list()

count = 1

if os.path.isfile('ignorelist'):
    print("Loading ignore list")
    with open('ignorelist') as f:
        ignore_list = f.read().splitlines()
    f.close()


# Print and log the tetxt
def LogAndPrint(text):
    tmp = str(text)
    tmp = text.replace("\n", "")
    print(tmp)
    open(file='log', mode='a', encoding='utf-8')
    f_log = open(
        'log',
        'a',
    )
    f_log.write(tmp + "\n")
    f_log.close()


def CheckRateLimit():
    c = threading.Timer(rate_limit_update_time, CheckRateLimit)
    c.daemon = True
    c.start()

    global ratelimit
    global ratelimit_search

    if ratelimit[2] < min_ratelimit:
        print("Ratelimit too low -> Cooldown (" + str(ratelimit[2]) + "%)")
        time.sleep(200)

        r = api.request('application/rate_limit_status').json()

        if 'resources' in r:
            for res_family in r['resources']:
                for res in r['resources'][res_family]:
                    limit = r['resources'][res_family][res]['limit']
                    remaining = r['resources'][res_family][res]['remaining']
                    percent = float(remaining) / float(limit) * 100

                    if res == "/application/rate_limit_status":
                        ratelimit = [limit, remaining, percent]

                    # print(res_family + " -> " + res + ": " + str(percent))
                    if percent < 5.0:
                        LogAndPrint(res_family + " -> " + res + ": " +
                                    str(percent) +
                                    "  !!! <5% Emergency exit !!!")
                        sys.exit(res_family + " -> " + res + ": " +
                                 str(percent) + "  !!! <5% Emergency exit !!!")
                    elif percent < 30.0:
                        LogAndPrint(res_family + " -> " + res + ": " +
                                    str(percent) + "  !!! <30% alert !!!")
                    elif percent < 70.0:
                        print(res_family + " -> " + res + ": " + str(percent))


# --- Login to Twitter using selenium
def login():
    url = (base_url + login_path)
    browser.implicitly_wait(30)
    browser.get(url)
    browser.find_element_by_xpath(
        "(//input[@name='session[username_or_email]'])[2]").click()
    browser.find_element_by_xpath(
        "(//input[@name='session[username_or_email]'])[2]").clear()
    browser.find_element_by_xpath(
        "(//input[@name='session[username_or_email]'])[2]").send_keys(
            username_or_email)
    browser.find_element_by_xpath(
        "(//input[@name='session[password]'])[2]").clear()
    browser.find_element_by_xpath(
        "(//input[@name='session[password]'])[2]").send_keys(password)
    browser.find_element_by_xpath("//button[@type='submit']").click()
    WebDriverWait(browser, 10)


def is_user_bot_hunter(username):
    username = username.replace("0", "o").lower()
    for i in bannedusers:
        if i in username:
            return True
        else:
            return False


# --- Run all search queries using Beautiful Soup
def ScanForContests():
    global count

    for search_query in search_queries:

        print("Getting new results for: " + search_query)

        url = (base_url + query_string + search_query)

        # ---selenium command
        browser.get(url)
        # ---soup command
        # r= requests.get(url)

        time.sleep(1)

        body = browser.find_element_by_tag_name('body')

        for _ in range(10):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)

        # ---soup commands
        data = browser.page_source.encode("utf-8")
        soup = BeautifulSoup(data, 'html.parser', from_encoding='utf-8')

        for details in soup.find_all(
                'div', attrs={'class': 'js-actionable-tweet'}):
            try:
                user_id = str(details['data-user-id'])
                tweet_id = str(details['data-tweet-id'])
                data_name = details['data-name']
                if user_id not in ignore_list and\
                        tweet_id not in ignore_list and\
                        is_user_bot_hunter(data_name) is False:
                    div = details.find('div', {'class': 'content'})
                    tweet_text = div.find('div', {
                        'class': 'js-tweet-text-container'
                    }).text.strip().encode("utf-8")
                    temp = details['data-screen-name'].encode("utf-8")
                    user_name = str(temp)
                    print('*********************')
                    # if "bot" not in str(details['data-name'].
                    #                   encode("utf-8").lower()):

                    print('{}\nUser ID: {}\nTweet ID: {}\nTweet: {}\n'.format(
                        user_name, user_id, tweet_id, tweet_text))
                    # if

            # TODO: add to listb
                count += 1
            except KeyError as e:
                print('Error extracting ' + str(e) + ' data from class:')
                print('*********************************')
                print(json.dumps(details.attrs, indent=4, sort_keys=True))
                SystemExit()
        # end for details in soup.find_all(...)
        print('Total found: ' + str(count))
    # end for search_query in search_queries


# end ScanForContests
login()
ScanForContests()
