import requests
from bs4 import BeautifulSoup
import re
import time
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#TODO Use the button of search series instead of the freeword

COLLECTION_SERIES_DICT = {
 #   'BOOSTER PACK ROMANCE DAWN- [OP-01]': {'series': '?series=556105', 'code': 'OP01', 'sheet_number': 0},
    #'BOOSTER PACK Paramount War- [OP-02]': {'series': '?series=556105', 'code': 'OP02', 'sheet_number': 1},
    'Promotion Card': {'series': '?series=556105', 'code': None, 'sheet_number': 5},
    'BOOSTER PACK Pillars of Strength- [OP-03]': {'series': '?series=556105', 'code': 'OP03', 'sheet_number': 2},
    'BOOSTER PACK kingdom of Intrigue- [OP-04]': {'series': '?series=556105', 'code': 'OP04', 'sheet_number': 3},
    'BOOSTER PACK Awakening of the New Era- [OP-05]': {'series': '?series=556105', 'code': 'OP05', 'sheet_number': 4},
}

MAX_RETRIES = 500
RETRY_DELAY = 60  # in seconds


def get_card_list(url: str, cards_image_values: list, collection_code: str):
    data = []
    for img in cards_image_values:
        img_url = url + img['src']
        img_url = f'=IMAGE("{img_url}")'
        if collection_code:
            regex_text = r'%s-\d{3}(_p\d)?' % collection_code
            collection_number = re.search(regex_text, img['src'])
            if collection_number and not any([collection_number.group() == card[0] for card in data]):
                print(f"Getting {img['alt']}...")
                data.append((collection_number.group(), img['alt'], img_url))
        else:
            if any([collection_number.group() == card[0] for card in data]):
                print(f"Getting {img['alt']}...")
                data.append((collection_number.group(), img['alt'], img_url))


    return data


def add_card_to_sheets(data_to_insert: list, sheet_number: int):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('/home/tc962/Downloads/op-planilha-f607b95831c3.json',
                                                             scope)
    client = gspread.authorize(creds)
    # CHANGE SHEET FOR COLLECTION, the number is the page-1
    # If its the second page the nuber is 1
    sheet = client.open("op_collection").get_worksheet(sheet_number)

    retries = 0
    card_idx = 0
    while retries < MAX_RETRIES:
        try:
            for name, img_url, image in data_to_insert[card_idx:]:
                logging.info(f'Card Index to insert: {card_idx}')
                if card_idx == len(data_to_insert):
                    break
                sheet.append_row([name, img_url, image.replace("'", "")], 'USER_ENTERED')
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
        print("Failed to retrieve the webpage.")
        exit()

    for collection_name, collection_details in COLLECTION_SERIES_DICT.items():
        logging.info(f'Runnging for collection {collection_name}')
        form_response = send_search_form(base_url_response=response, collection_search=collection_name,
                                         collection_series=collection_details['series'])

        soup_after_form = BeautifulSoup(form_response.content, 'html.parser')

        cards_img = soup_after_form.find_all('img')

        cards_list = get_card_list(url=one_piece_website_url, cards_image_values=cards_img,
                                   collection_code=collection_details['code'])
        add_card_to_sheets(cards_list, collection_details['sheet_number'])
