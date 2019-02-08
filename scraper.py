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
from requests_oauthlib import OAuth1

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
scan_update_time = data["scan-update-time"]
rate_limit_update_time = data["rate-limit-update-time"]
min_ratelimit = data["min-ratelimit"]
min_ratelimit_retweet = data["min-ratelimit-retweet"]
username_or_email = data["username-or-email"]
password = data["password"]
bannedusers = data["banned"]
# End loaded data from config file

base_url = 'https://twitter.com/'
query_string = 'search?q='
login_path = 'login'
loginError = "The username and password you entered did not match Twitter's records.  " + \
    "Please double-check and try again."
# ---selenium command
browser = webdriver.Chrome()
auth = OAuth1(consumer_key, consumer_secret, access_token_key, access_token_secret)

# --- TwitterAPI OAuth command
api = TwitterAPI(consumer_key, consumer_secret, access_token_key,
                 access_token_secret)
post_list = list()
ignore_list = list()
ratelimit = [999, 999, 100]  # [limit,remaining,percent]
count = 1

if os.path.isfile('ignorelist'):
    print("Loading ignore list")
    with open('ignorelist') as f:
        ignore_list = f.read().splitlines()
    f.close()


# --- Print and log the tetxt
def LogAndPrint(text):
    tmp = str(text)
    tmp = text.replace("\n", "")
    print(tmp)
    f_log = open(file='log', mode='a', encoding='utf-8')
    f_log.write(tmp + "\n")
    f_log.close()
# end LogAndPrint(text)


def CheckError(r):
    r = r.json()
    if 'errors' in r:
        LogAndPrint("Error message: " + r['errors'][0]
                    ['message'] + " Code: " + str(r['errors'][0]['code']))
# end CheckError(r)


# --- Login to Twitter using selenium
def Login():
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
    new_page = browser.find_element_by_tag_name('html')
    if('https://twitter.com/login/error?' in new_page.id):
        LogAndPrint(loginError)
        sys.exit(loginError)


# --- check if user is a bot hunter
def is_user_bot_hunter(username):
    username = username.replace("0", "o").lower()
    for i in bannedusers:
        if i in username:
            return True
        else:
            return False


# --- Run all search queries using Beautiful Soup
def ScanForContests():
    t = threading.Timer(scan_update_time, ScanForContests)
    t.daemon = True
    t.start()

    global count
    global ratelimit_search

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
                print('USERNAMEUSERNAME:' + user_id)
                if user_id not in ignore_list and\
                        tweet_id not in ignore_list and\
                        is_user_bot_hunter(data_name) is False:
                    div = details.find('div', {'class': 'content'})
                    tweet_text = str(div.find('div', {
                        'class': 'js-tweet-text-container'
                    }).text.strip())
                    user_name = str(details['data-screen-name'])
                    print('*********************')
                    # .format(user_name, user_id, tweet_id, tweet_text))
                    print(f'{user_name}\nUser ID: {user_id}')
                    print(f'Tweet ID: {tweet_id}\nTweet: {tweet_text}')
                    f_ign = open('ignorelist', 'a')
                    ignore_list.append(tweet_id)
                    f_ign.close()
                    api.request('statuses/retweet/:' + tweet_id)
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


Login()
# CheckRateLimit()
while (True):
    ScanForContests()
    time.sleep(3600)
