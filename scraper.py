# ---Import needed modules
import time
import threading
import sys
import json
import os.path
# ---Import needed modules from Twitter
from TwitterAPI import TwitterAPI
# ---Import needed modules from Selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
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
follow_keywords = data["follow-keywords"]
fav_keywords = data["fav-keywords"]
# End l oaded data from config file

base_url = 'https://twitter.com/'
query_string = 'search?q='
login_path = 'login'
loginError = "The username and password you entered did not match Twitter's records.  " + \
    "Please double-check and try again."
# ---selenium commands
chrome_options = Options()
chrome_options.add_argument("--headless")
browser = webdriver.Chrome(options=chrome_options)
# browser = webdriver.Chrome()
auth = OAuth1(consumer_key, consumer_secret, access_token_key, access_token_secret)

# --- TwitterAPI OAuth command
api = TwitterAPI(consumer_key, consumer_secret, access_token_key,
                 access_token_secret)
post_list = list()
ignore_list = list()
ratelimit = [999, 999, 100]  # [limit,remaining,percent]
count = 0


# --- Print and log the tetxt
def LogAndPrint(text):
    tmp = str(text)
    # tmp = text.replace("\n", "")
    print(tmp)
    f_log = open(file='log', mode='a', encoding='utf-8')
    f_log.write(tmp + "\n")
    f_log.close()
# end LogAndPrint(text)


if os.path.isfile('ignorelist'):
    LogAndPrint("Loading ignore list")
    with open('ignorelist') as f:
        ignore_list = f.read().splitlines()
    f.close()


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
    for i in bannedusers:
        if username in i:
            return True
    username = username.replace("0", "o").lower()
    for i in bannedusers:
        if username in i:
            return True
    return False


# --- Run all search queries using Beautiful Soup
def ScanForContests():
    t = threading.Timer(scan_update_time, ScanForContests)
    t.daemon = True
    t.start()

    global count
    global ratelimit_search

    for search_query in search_queries:
        search_query_result_count = 0
        LogAndPrint("Getting new results for: " + search_query)

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
                        not is_user_bot_hunter(data_name):

                    post_list.append(details)
                    f_ign = open('ignorelist', 'a')
                    ignore_list.append(tweet_id)
                    f_ign.write(tweet_id + "\n")
                    f_ign.close()
                    search_query_result_count += 1
            except KeyError as e:
                LogAndPrint('Error extracting ' + str(e) + ' data from class:')
                LogAndPrint('*********************************')
                LogAndPrint(json.dumps(details.attrs, indent=4, sort_keys=True))
                SystemExit()
        # end for details in soup.find_all(...)
        count = count + search_query_result_count
        if search_query_result_count == 1:
            LogAndPrint(str(search_query_result_count) + ' entry found')
        else:
            LogAndPrint(str(search_query_result_count) + ' entries found')

    LogAndPrint('Total found: ' + str(count))
    # end for search_query in search_queries
# end ScanForContests


def UpdateQueue():
    u = threading.Timer(retweet_update_time, UpdateQueue)
    u.daemon = True
    u.start()

    global count

    LogAndPrint("******** GETTING READY TO RETWEET ***********")
    LogAndPrint("******** Queue length: " + str(len(post_list)))
    while(len(post_list) > 0):
        details = post_list[0]
        div = details.find('div', {'class': 'content'})
        tweet_text = str(div.find('div', {
            'class': 'js-tweet-text-container'}).text.strip())
        user_name = str(details['data-screen-name'])
        user_id = str(details['data-user-id'])
        tweet_id = str(details['data-tweet-id'])
        LogAndPrint(f'{user_name}\nUser ID: {user_id}')
        LogAndPrint(f'Tweet ID: {tweet_id}\nTweet: {tweet_text}')

        CheckForFollowRequest(details)
        CheckForFavoriteRequest(details)

        r = api.request('statuses/retweet/:' + tweet_id)
        CheckError(r)
        post_list.pop(0)
        count -= 1


def CheckForFollowRequest(item):
    div = item.find('div', {'class': 'content'})
    tweet_text = str(div.find('div', {
        'class': 'js-tweet-text-container'}).text.strip())
    user_name = str(item['data-screen-name'])

    if any(x in tweet_text.lower() for x in follow_keywords):
        try:
            r = api.request(
                'friendships/create', {'screen_name': user_name})
            CheckError(r)
            LogAndPrint("Follow: " + user_name)
        except KeyError:
            LogAndPrint("Friendship request error")
            # screen_name = str(item['data-screen-name'])
            # r = api.request('friendships/create',
            #                 {'screen_name': screen_name})
            # CheckError(r)
            # LogAndPrint("Follow: " + screen_name)


def CheckForFavoriteRequest(item):
    div = item.find('div', {'class': 'content'})
    tweet_text = str(div.find('div', {
        'class': 'js-tweet-text-container'}).text.strip())
    tweet_id = str(item['data-tweet-id'])

    if any(x in tweet_text.lower() for x in fav_keywords):
        try:
            r = api.request('favorites/create', {'id': tweet_id})
            CheckError(r)
            LogAndPrint("Favorite: " + tweet_id)
        except KeyError:
            LogAndPrint("Favorite Error")
            # r = api.request('favorites/create', {'id': item['id']})
            # CheckError(r)
            # LogAndPrint("Favorite: " + str(item['id']))


Login()
# CheckRateLimit()
while (True):
    ScanForContests()
    UpdateQueue()
    time.sleep(3600)
