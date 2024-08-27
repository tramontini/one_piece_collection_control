import requests
from bs4 import BeautifulSoup
import re
import time
import gspread
import logging
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#TODO Use the button of search series instead of the freeword

# In your google sheet, create as many sheets as there are collections in here (20)
COLLECTION_SERIES_DICT = {
    'OP-01': {'series': '?series=550101', 'code': 'OP01', 'sheet_number': 0},
    'OP-02': {'series': '?series=550102', 'code': 'OP02', 'sheet_number': 1},
    'OP-03': {'series': '?series=550103', 'code': 'OP03', 'sheet_number': 2},
    'OP-04': {'series': '?series=550104', 'code': 'OP04', 'sheet_number': 3},
    'OP-05': {'series': '?series=550105', 'code': 'OP05', 'sheet_number': 4},
    'OP-06': {'series': '?series=550106', 'code': 'OP06', 'sheet_number': 5},
    'OP-07': {'series': '?series=550107', 'code': 'OP07', 'sheet_number': 6},
    'OP-08': {'series': '?series=550108', 'code': 'OP08', 'sheet_number': 7},
    'OP-09': {'series': '?series=550109', 'code': 'OP09', 'sheet_number': 8},
    'ST-01': {'series': '?series=550001', 'code': 'ST01', 'sheet_number': 9},
    'ST-02': {'series': '?series=550002', 'code': 'ST02', 'sheet_number': 10},
    'ST-03': {'series': '?series=550003', 'code': 'ST03', 'sheet_number': 11},
    'ST-04': {'series': '?series=550004', 'code': 'ST04', 'sheet_number': 12},
    'ST-05': {'series': '?series=550005', 'code': 'ST05', 'sheet_number': 13},
    'ST-06': {'series': '?series=550006', 'code': 'ST06', 'sheet_number': 14},
    'ST-07': {'series': '?series=550007', 'code': 'ST07', 'sheet_number': 15},
    'ST-08': {'series': '?series=550008', 'code': 'ST08', 'sheet_number': 16},
    'ST-09': {'series': '?series=550009', 'code': 'ST09', 'sheet_number': 17},
    'ST-10': {'series': '?series=550010', 'code': 'ST10', 'sheet_number': 18},
    'ST-11': {'series': '?series=550011', 'code': 'ST11', 'sheet_number': 19},
}

MAX_RETRIES = 500
RETRY_DELAY = 60  # in seconds


def get_card_list(cards_image_values: list):
    data = []
    # Change to the URL for the card list site with URI of /images/cardlist/card/
    base_image_url = "https://www.onepiece-cardgame.com/images/cardlist/card/"

    for img in cards_image_values:
        # Extract the correct filename from `data-src` using regex
        regex_text = r'(?<=card/)(.*?)(?=\.png)'
        match = re.search(regex_text, img['data-src'])
        
        if match:
            image_filename = match.group()
            img_url = f'{base_image_url}{image_filename}.png'
            img_url = f'=IMAGE("{img_url}")'

            logging.info(f"Processing image - URL: {img_url}, ALT: {img['alt']}")

            # Check if the collection number is already in the list to avoid duplicates
            if not any([image_filename == card[0] for card in data]):
                print(f"Getting {img['alt']}...")
                data.append((image_filename, img['alt'], img_url))

    return data


def add_card_to_sheets(data_to_insert: list, sheet_number: int):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credential.json', scope)
    client = gspread.authorize(creds)

    # Change the first parameter to the name of your sheet, make sure to share it with the service account's email in the credential.json
    sheet = client.open("One Piece Collection (JP)").get_worksheet(sheet_number)

    retries = 0
    card_idx = 0
    while retries < MAX_RETRIES:
        try:
            for name, card_name, image in data_to_insert[card_idx:]:
                logging.info(f'Card Index to insert: {card_idx}')
                if card_idx == len(data_to_insert):
                    break
                
                # Add a random delay between 1 and 2 seconds
                time.sleep(random.uniform(1, 2))
                
                sheet.append_row([name, card_name, image.replace("'", "")], 'USER_ENTERED')
                card_idx += 1
            break
        except gspread.exceptions.APIError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                logging.warning(f"Rate limit exceeded. Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
                retries += 1
            else:
                raise
    else:
        logging.error("Max retries reached. Exiting.")

def send_search_form(base_url_response: requests.Response, collection_search: str, collection_series: str) -> requests.Response:
    soup = BeautifulSoup(base_url_response.content, 'html.parser')
    form = soup.find('form')
    form_action = one_piece_website_url + collection_series + form['action']

    form_data = {}
    for input_tag in form.find_all('input'):
        name = input_tag.get('name')
        if name == 'freewords':
            form_data[name] = collection_search

    return requests.post(form_action, data=form_data)

def get_card_images(soup):
    # This regex will match filenames like "OP03-001", "OP03-002", etc.
    card_images = []
    regex_pattern = r'.*/card/OP\d{2}.*\.png'

    # Loop through all img tags
    for img in soup.find_all('img', class_='lazy'):
        data_src = img.get('data-src')
        if data_src and re.search(regex_pattern, data_src):
            # If it matches the pattern, add it to the list
            card_images.append(img)

    return card_images

if __name__ == '__main__':
    # Change to the URL for the card list site with URI of /cardlist/
    one_piece_website_url = "https://www.onepiece-cardgame.com/cardlist/"
    response = requests.get(one_piece_website_url)

    if response.status_code != 200:
        logging.info("Failed to retrieve the webpage.")
        exit()

    for collection_name, collection_details in COLLECTION_SERIES_DICT.items():
        logging.info(f'Running for collection {collection_name}')
        form_response = send_search_form(base_url_response=response, collection_search=collection_name,
                                         collection_series=collection_details['series'])
        print(form_response)

        soup_after_form = BeautifulSoup(form_response.content, 'html.parser')

        cards_img = get_card_images(soup_after_form)

        cards_list = get_card_list(cards_image_values=cards_img)
        add_card_to_sheets(cards_list, collection_details['sheet_number'])
