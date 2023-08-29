import aiohttp
import asyncio
import re
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, SoupStrainer
from django.shortcuts import render
from django.http import HttpResponse

async def fetch_content(session, url):
    try:
        async with session.get(url) as response:
            return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

async def extract_price(soup):
    price_pattern = r"\$\d+\.\d+|\£\d+|\d+\.\d+\s(?:USD|EUR)"
    prices = re.findall(price_pattern, soup.text)
    return prices[0] if prices else "Price not found"

async def extract_product_data(element, html_content):
    product_soup = BeautifulSoup(html_content, "lxml")
    product_price = await extract_price(product_soup)
    parent_element = element.find_parent()
    product_link = parent_element.get("href")
    return {
        "link": product_link.strip(),
        "price": product_price,
        "name": element.strip(),
        "parent_element": parent_element,
    }

async def fetch_sub_links(session, parent_href_formatted, product_name, sub_links, timeout=3):
    try:
        async with session.get(parent_href_formatted, timeout=timeout) as response:
            content = await response.read()
            sub_soup = BeautifulSoup(content, "html.parser", parse_only=SoupStrainer("a", href=True), on_duplicate_attribute="replace")
            sub_atags = sub_soup.find_all("a", href=True)
            for sub_atag in sub_atags:
                href_sub = sub_atag.get("href")
                sub_href = urljoin(parent_href_formatted, href_sub)
                sub_href = urlparse(sub_href).geturl()
                sub_links.append(sub_href)
                print(sub_href)
    except asyncio.TimeoutError:
        print(f"Timeout fetching sub links from {parent_href_formatted}")
    except Exception:
        pass
        
async def get_sub_links(session, soup, product_name, website_name):
    sub_links = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36"
    }

    getUrl = await get_url_formatting(product_name, website_name)

    get_parent_url = set(soup.find_all("a", href=True))

    tasks = []
    for link in get_parent_url:
        parent_href = link.get("href")
        parent_href_formatted = urljoin(f"https://www.{website_name}.com.au", parent_href)
        parent_href_formatted = urlparse(parent_href_formatted).geturl()
        sub_links[parent_href_formatted] = []
        tasks.append(fetch_sub_links(session, parent_href_formatted, product_name, sub_links[parent_href_formatted]))

    await asyncio.gather(*tasks)

    return sub_links

async def get_url_formatting(product_name, website_name):
    product_end_formatted = product_name.replace(" ", "%20")
    product_formatted = product_name.replace(" ", "+")
    website_urls = {
        "rebelsport": f"https://www.rebelsport.com.au/search?q={product_end_formatted}",
        "harveynorman": f"https://www.harveynorman.com.au/search?q={product_formatted}",
        "ebay": f"https://www.ebay.com.au/sch/i.html?_from=R40&_trksid=p4432023.m570.l1313&_nkw={product_formatted}&_sacat=0",
        "thegoodguys": f"https://www.thegoodguys.com.au/SearchDisplay?categoryId=&storeId=900&catalogId=30000&langId=-1&sType=SimpleSearch&resultCatEntryType=2&showResultsPage=true&searchSource=Q&pageView=&beginIndex=0&orderBy=0&pageSize=30&searchTerm={product_formatted}",
        "kogan": f"https://www.kogan.com/au/shop/?q={product_formatted}",
        "officeworks": f"https://www.officeworks.com.au/shop/officeworks/search?q={product_end_formatted}&view=grid&page=1&sortBy=bestmatch",
        "jbhifi": f"https://www.jbhifi.com.au/search?page=1&query={product_end_formatted}&saleItems=false&toggle%5BonPromotion%5D=false",
        "ajeworld": f"https://ajeworld.com.au/collections/shop?q={product_formatted}",
        "myer": f"https://www.myer.com.au/search?query={product_formatted}",
    }
    if website_name not in website_urls:
        print("Unsupported website name:", website_name)
        return None

    url_formatted = website_urls[website_name]
    return url_formatted

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

async def get_soup(url_):
    html = await fetch_html(url_)
    if html:
        return BeautifulSoup(html, "lxml")
    else:
        print(f"Failed to fetch the webpage: {url_}")
        return None

async def search_view(request):
    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        website_name = request.POST.get('website_name')
        product_data = await main(product_name, website_name)
        return render(request, 'productScraper/search_results.html', {'product_data': product_data})
    
    return render(request, 'productScraper/search_form.html')

async def main(product_name, website_name):
    formatted_url = await get_url_formatting(product_name, website_name)
    print(f"Now searching for {product_name} in url {formatted_url}")

    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        soup = await get_soup(formatted_url)

        if soup:
            product_data, count, sub_links_dict = await extract_product_data(
                product_name, session
            )

            for product_info in product_data.values():
                print(f"Product Info:\n {product_info}\n")

            print(f"Total number of products found: {count}")

            sub_links_dict = await get_sub_links(session, soup, product_name, website_name)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total time taken: {elapsed_time:.2f} seconds")
    return product_data
