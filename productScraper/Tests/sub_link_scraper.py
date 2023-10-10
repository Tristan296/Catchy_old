import aiohttp
import asyncio
import re
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup, SoupStrainer


async def get_url_formatting(product_name, website_name):
    product_end_formatted = product_name.replace(" ", "%20")
    product_formatted = product_name.replace(" ", "+")
    website_urls = {
        "rebelsport": f"https://www.rebelsport.com.au/search?q={product_end_formatted}",
        "harveynorman": f"https://www.harveynorman.com.au/catalogsearch/result/?q={product_formatted}",
        "ebay": f"https://www.ebay.com.au/sch/i.html?_from=R40&_trksid=p4432023.m570.l1313&_nkw={product_formatted}&_sacat=0",
        "thegoodguys": f"https://www.thegoodguys.com.au/SearchDisplay?categoryId=&storeId=900&catalogId=30000&langId=-1&sType=SimpleSearch&resultCatEntryType=2&showResultsPage=true&searchSource=Q&pageView=&beginIndex=0&orderBy=0&pageSize=30&searchTerm={product_formatted}",
        "kogan": f"https://www.kogan.com/au/shop/?q={product_formatted}",
        "officeworks": f"https://www.officeworks.com.au/shop/officeworks/search?q={product_end_formatted}&view=grid&page=1&sortBy=bestmatch",
        "jbhifi": f"https://www.jbhifi.com.au/search?page=1&query={product_end_formatted}&saleItems=false&toggle%5BonPromotion%5D=false",
        "ajeworld": f"https://ajeworld.com.au/collections/shop?q={product_formatted}",
        "myer": f"https://www.myer.com.au/search?query={product_formatted}",
        "nike": f"https://www.nike.com/au/w?q={product_end_formatted}&vst={product_end_formatted}"
    }
    if website_name not in website_urls:
        print("Unsupported website name:", website_name)
        return None

    url_formatted = website_urls[website_name]
    return url_formatted


# Define a function to scrape links from a given URL
async def scrape_links(session, url, timeout=None):
    try:
        async with session.get(url, timeout=timeout) as response:
            content = await response.read()
            soup = BeautifulSoup(content, "lxml", on_duplicate_attribute="replace")
            atags = soup.find_all("a", href=True)
            link_results = []
            for atag in atags:
                link = urljoin(url, atag["href"])
                link_text = atag.get_text()
                link_results.append((link, link_text))
                print(f"Link: {link}\nText: {link_text}\n")
            return link_results

    except asyncio.TimeoutError:
        print(f"Timeout scraping links from {url}")
    except Exception:
        pass

    return []

async def main(product_name, website_name):
    formatted_url = await get_url_formatting(product_name, website_name)
    print(f"Now searching for {product_name} in url {formatted_url}")

    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        soup = await get_soup(formatted_url)

        if soup:
            # Use the scrape_links function to get sub-links
            get_parent_url = await scrape_links(session, formatted_url)
            sub_links = []
            for link in get_parent_url:
                sub_links.extend(await scrape_links(session, link))

            # The rest of your code for extracting product details and processing sub-links
            # ...


async def get_soup(url_):
    html = await fetch_html(url_)
    if html:
        return BeautifulSoup(html, "lxml")
    else:
        print(f"Failed to fetch the webpage: {url_}")
        return None


async def fetch_html(url_):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url_, headers=headers) as response:
            if response.status == 200:
                return await response.text()
            else:
                return None

if __name__ == "__main__":
    product_name = "shoes"
    website_name = "myer"
    asyncio.run(main(product_name, website_name))
