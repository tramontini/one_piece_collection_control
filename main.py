import requests
from bs4 import BeautifulSoup
import re
import time
import gspread
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#TODO Use the button of search series instead of the freeword

COLLECTION_SERIES_DICT = {
    'OP-01': {'series': '?series=556101', 'code': 'OP01', 'sheet_number': 0},
    'OP-02': {'series': '?series=556102', 'code': 'OP02', 'sheet_number': 1},
    'OP-03': {'series': '?series=556103', 'code': 'OP03', 'sheet_number': 2},
    'OP-04': {'series': '?series=556104', 'code': 'OP04', 'sheet_number': 3},
    'OP-05': {'series': '?series=556105', 'code': 'OP05', 'sheet_number': 4},
    'Promotion': {'series': '?series=556901', 'code': None, 'sheet_number': 5},
    'ST-01': {'series': '?series=556001', 'code': 'ST01', 'sheet_number': 6},
    'ST-02': {'series': '?series=556002', 'code': 'ST02', 'sheet_number': 7},
    'ST-03': {'series': '?series=556003', 'code': 'ST03', 'sheet_number': 8},
    'ST-04': {'series': '?series=556004', 'code': 'ST04', 'sheet_number': 9},
    'ST-05': {'series': '?series=556005', 'code': 'ST05', 'sheet_number': 10},
    'ST-06': {'series': '?series=556006', 'code': 'ST06', 'sheet_number': 11},
    'ST-07': {'series': '?series=556007', 'code': 'ST07', 'sheet_number': 12},
    'ST-08': {'series': '?series=556008', 'code': 'ST08', 'sheet_number': 13},
    'ST-09': {'series': '?series=556009', 'code': 'ST09', 'sheet_number': 14},
    'ST-10': {'series': '?series=556010', 'code': 'ST10', 'sheet_number': 15},
    'ST-11': {'series': '?series=556011', 'code': 'ST11', 'sheet_number': 16},
}

MAX_RETRIES = 500
RETRY_DELAY = 60  # in seconds


def get_card_list(url: str, cards_image_values: list):
    data = []
    for img in cards_image_values:
        img_url = url + img['src']
        img_url = f'=IMAGE("{img_url}")'

        regex_text = r'(?<=card\/)(.*?)(?=\.png)'
        collection_number = re.search(regex_text, img['src'])
        if collection_number and not any([collection_number.group() == card[0] for card in data]):
            print(f"Getting {img['alt']}...")
            data.append((collection_number.group(), img['alt'], img_url))


    return data


def add_card_to_sheets(data_to_insert: list, sheet_number: int):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('op-planilha-f607b95831c3.json',
                                                             scope)
    client = gspread.authorize(creds)

    sheet = client.open("op_collection").get_worksheet(sheet_number)

    retries = 0
    card_idx = 0
    while retries < MAX_RETRIES:
        try:
            for name, card_name, image in data_to_insert[card_idx:]:
                logging.info(f'Card Index to insert: {card_idx}')
                if card_idx == len(data_to_insert):
                    break
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

if __name__ == '__main__':
    one_piece_website_url = "https://asia-en.onepiece-cardgame.com/cardlist/"
    response = requests.get(one_piece_website_url)

    if response.status_code != 200:
        logging.info("Failed to retrieve the webpage.")
        exit()

    for collection_name, collection_details in COLLECTION_SERIES_DICT.items():
        logging.info(f'Running for collection {collection_name}')
        form_response = send_search_form(base_url_response=response, collection_search=collection_name,
                                         collection_series=collection_details['series'])

        soup_after_form = BeautifulSoup(form_response.content, 'html.parser')

        cards_img = soup_after_form.find_all('img')

        cards_list = get_card_list(url=one_piece_website_url, cards_image_values=cards_img)
        add_card_to_sheets(cards_list, collection_details['sheet_number'])
