# Catchy

![GitHub](https://img.shields.io/github/license/Tristan296/Catchy)
![Python](https://img.shields.io/badge/python-v3.8%2B-blue)

<p align="center">
  <img src="https://github.com/Tristan296/Catchy/assets/109927879/1b8a9eb5-e06d-4a27-89aa-8e5f1ef2c988" width="70%"></img>
</p>

# What is Catchy?
Catchy's is a smart web-scraping application designed to extract the cheapest products from various e-commerce sites. 

# How it works
It extracts product info including product names, prices, images, and a link to the website. Hardcoding selector pathways is a common method used by web scrapers to scrape information. The problem is that web developers frequently update these html selectors, which breaks the code. Instead, we took a different technique, examining the website's soup for language containing the product name. If this method fails to locate any products, it will get all relevant product links on the site and swiftly search through these links to obtain product information.

The idea is for it to be able to compare pricing across multiple large ecommerce sites to get the best prices.  

# Features
- Retrieve product information from multiple e-commerce websites.
- Compare prices and details for the same product across different sources.
- Easy-to-use web interface.
- Utilizes aiohttp and BeautifulSoup libraries.

# Efficiency 
- Utilises `asyncio` asynchronous fetching of product information for improved performance.
- Utilises lxml for efficient parsing of soup
- When parsing for website links, SoupStrainer filters links in soup quickly.
- `aiohttp.ClientSession`:
  - Connection pooling: for faster subsequent requests to the same host
  - Concurrency: concurrently performing requests without blocking the execution of other tasks
- 3 second timeout for fetching links

# How to use 
Prerequisite:
**Ensure you have Python 3.8 or higher installed on your system. Then, install the required dependencies using pip:**
1. Clone the repository from https://github.com/Tristan296/Catchy.git
2. Install Dependencies:
```
pip install -r requirements.txt
```
3. Start the server and open it:
```python
python3 productScraper/manage.py runserver 9000
```
4. Fill out the form and products will be displayed:
<img width="352" alt="Screenshot 2023-08-10 at 6 36 56 pm" src="https://github.com/Tristan296/productScraper/assets/109927879/70391c60-69c3-4f52-8267-c818e770d3b0">
<img width="233" height="253" alt="image" src="https://github.com/Tristan296/productScraper/assets/109927879/006fee92-2dec-4714-b0b8-4d77e32a249d">


# Supported websites
| Website       | Support     |
| -----------   | ----------- |
| Rebel Sport   |✅           |
 

