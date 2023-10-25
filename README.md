# One Piece TCG Card Collector

A tool to scrape card details from the One Piece TCG website and save them to Google Sheets for easy collection management.

## Overview

This tool is designed for One Piece TCG enthusiasts who want to track and manage their card collections efficiently. With just a few steps, you can extract card details from the official One Piece TCG website and save them directly to a Google Sheet.

## Features

- **Web Scraping**: Uses Python with `requests` and `BeautifulSoup` to fetch and parse card details.
- **Google Sheets Integration**: Utilizes `gspread` to save the card details to a Google Sheet.

## Prerequisites

- Python 3.x
- A Google Cloud account (for Google Sheets API access)

## Google Sheets API Setup:
- Follow the guide [here](https://gspread.readthedocs.io/en/latest/oauth2.html) to set up the Google Sheets API and obtain your `credentials.json`.
- Place the `credentials.json` in the root directory of the project.

## Google Sheets Setup
Change the name of op_collection to your sheet name, and don't forget to change the index of the sheets in the collection dict the way you want
```sheet = client.open("op_collection").get_worksheet(sheet_number)```

## Sheets Screenshot
![image](https://github.com/tramontini/one_piece_collection_control/assets/25264937/16f38088-49f0-4481-9cfe-f3cdb290a6f4)



## Contributing
Feel free to send any customization, bug fix or improvements! Just send your PR!
