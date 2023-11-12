import aiohttp
import asyncio
import re
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, SoupStrainer
from django.shortcuts import render
from django.http import HttpResponse


async def fetch_price(session, product_link):
    try:
        async with session.get(product_link) as response:
            html_content = await response.text()
            return html_content
    except Exception as e:
        print(f"Error fetching {product_link}: {e}")
        return None


async def fetch_sub_links(
    session, parent_href_formatted, product_name, sub_links, website_name, timeout=10
):
    try:
        async with session.get(parent_href_formatted, timeout=timeout) as response:
            content = await response.read()
            sub_soup = BeautifulSoup(
                content,
                "lxml",
                parse_only=SoupStrainer(["a", "div", "span"]), 
            )
            sub_links_count = 0
            sub_links_with_prices = []
            sub_links_set = set()  # Create a set to store unique sub-links
            sub_atags = sub_soup.find_all("a", href=True)
            
            for sub_atag in sub_atags:
                href_sub = sub_atag.get("href")
                sub_href = urljoin(parent_href_formatted, href_sub)
                sub_href = urlparse(sub_href).geturl()
                
                # Ensure the website is a myer one, not a social media one 
                # and that the product being searched for is in the link
                # before finding related details.
                if website_name in sub_href and product_name in sub_href:
                    sub_links_count += 1
                    sub_links_with_prices.append({
                        "link": sub_href,
                        "price": await get_sublink_price(session, sub_href),
                        "count": sub_links_count,
                        "imageURL" : await fetch_product_image(sub_soup, session, product_name, sub_href)
                    })
                    
                else:
                    print(f"website {sub_href} isn't a valid link")

        return sub_links_with_prices

    except asyncio.TimeoutError:
        print(f"Timeout fetching sub links from {parent_href_formatted}")
    except Exception as e:
        print(f"Error fetching sub links from {parent_href_formatted}: {e}")
    except Exception:
        pass

    return []
    
    
async def get_sublink_price(session, sub_href):
    try:
        async with session.get(sub_href) as response:
            html_content = await response.text()
            price_pattern = r"\$\d+\.\d+|\£\d+|\d+\.\d+\s(?:USD|EUR)"
            prices = re.findall(price_pattern, html_content)
            return prices[0] if prices else "Price not found"
    except Exception:
        return "Price not found"
    

async def get_product_sub_links(session, soup, product_name, website_name):
    sub_links = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36"
    }

    getUrl = await get_url_formatting(product_name, website_name)

    get_parent_url = set(soup.find_all("a", href=True))

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [
            fetch_sub_links(session, urljoin(f"https://www.{website_name}.com.au", link.get("href")), product_name, getUrl, website_name)
            for link in get_parent_url
        ]
        sub_links_with_prices = await asyncio.gather(*tasks)

    # Merge the sub-links with prices from all tasks into one list
    for links_with_prices in sub_links_with_prices:
        sub_links.extend(links_with_prices)

    return sub_links


async def fetch_product_image(soup, session, product_name, product_link):
    try:
        image_tags = soup.find_all("img")

        for img_tag in image_tags:
            img_url = img_tag.get("src") 
            img_tag_str = str(img_tag.get("description"))
            if img_url:
                return img_url 
            else:
                return "N/A"
        
    except Exception as e:
        print(f"Error fetching image from {product_link}: {e}")
        
async def extract_product_info(soup, product_name, website_name, session):
    count = 0
    product_data = {}
    sub_links_dict = {}
    sub_links_with_prices = []
    pattern = re.compile(re.escape(product_name), re.IGNORECASE)
    matched_elements = soup.find_all(string=pattern)

    tasks = [
        fetch_price(session, parent_element.get("href"))
        for element in matched_elements
        if (parent_element := element.find_parent()) is not None
        and (product_link := parent_element.get("href")) is not None
        and product_link.startswith(("http://", "https://"))
    ]
    html_contents = await asyncio.gather(*tasks)

    print("Number of html_contents:", len(html_contents))

    if len(html_contents) <= 10:
        # Collect sub-links with prices and add them to sub_links_with_prices
        sub_links_with_prices = await get_product_sub_links(session, soup, product_name, website_name)
        
        return product_data, sub_links_with_prices

async def extract_product_price(html_content):
    price_pattern = r"\$\d+\.\d+|\£\d+|\d+\.\d+\s(?:USD|EUR)"
    prices = re.findall(price_pattern, html_content)
    return prices[0] if prices else "Price not found"


async def create_product_info(name, link, price, parent_element, image_url):
    return {
        "name": name,
        "link": link,
        "price": price,
        "parent_element": parent_element,
        "image_url": image_url
    }


async def extract_nearest_price(soup, image_src, product_name):
    # Define words to check for in the extracted price
    words_to_check = ["discount", "sale", "offer", "special"]

    # Define your logic to find the nearest price element to the image
    # For example, you can look for a price element within the same parent element as the image
    # Customize this logic based on the HTML structure of the website you are scraping
    price_element = soup.find("span", text=re.compile(r'\$\d+\.\d+'))  # Modify this based on your HTML structure

    if price_element:
        price_text = price_element.get_text()
        # Check if any of the words to check are in the price text
        if any(word in price_text.lower() for word in words_to_check):
            # If any word is found, get the price from the parent element
            parent_price_element = soup.find("span", text=re.compile(r'\$\d+\.\d+'))
            if parent_price_element:
                return parent_price_element.get_text()
        else:
            return price_text

    return "Price not found"


async def process_matched_elements(product_name, matched_elements, html_contents, product_data):
    count = 0
    for i, element in enumerate(matched_elements):
        parent_element = element.find_parent()
        product_link = parent_element.get("href")

        if product_link is None or not product_link.startswith(("http://", "https://")):
            continue

        if i >= len(html_contents):
            continue

        product_price = await extract_product_price(html_contents[i])
        if not product_price:
            continue

        # Extract the nearest price to the image
        async with aiohttp.ClientSession() as session:
            soup = await get_soup(product_link)
            nearest_price = await extract_nearest_price(soup, image_url, product_name)
        
        product_info = await create_product_info(
         element.strip(), product_link.strip(), nearest_price, parent_element, image_url
        )

        # # Add the image URL to the product info
        # product_info["image_url"] = image_url

        product_data[element.strip()] = product_info
        count += 1


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

async def search_view(request):
    if request.method == "POST":
        product_name = request.POST.get("product_name")
        website_name = request.POST.get("website_name")

        async with aiohttp.ClientSession() as session:
            results = await main(product_name, website_name, session)

            # Separate the results into product_data and sub_links_with_prices
            product_data, sub_links_with_prices = results

        return render(
            request,
            "productScraper/search_results.html",
            {"product_data": product_data, "sub_links_with_prices": sub_links_with_prices},
        )

    return render(request, "productScraper/search_form.html")

async def main(product_name, website_name, session):
    formatted_url = await get_url_formatting(product_name, website_name)
    print(f"Now searching for {product_name} in url {formatted_url}")

    start_time = time.time()

    soup = await get_soup(formatted_url)

    if soup:
        product_data, sub_links_with_prices = await extract_product_info(
            soup, product_name, website_name, session
        )
       
        # Call fetch_product_image to retrieve product images
        # product_images = await fetch_product_image(soup, session, product_name, product_data)
        # print(product_images)
        # for product_info in product_data.values():
        #     print(f"Product Info:\n {product_info}\n")

        # for sub_link_info in sub_links_with_prices:
        #     print(f"Sub-Link Info:\n {sub_link_info}\n")
            
        print(sub_links_with_prices)
        print(f"Total number of products found: {len(product_data or sub_links_with_prices)}")

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total time taken: {elapsed_time:.2f} seconds")
    return product_data, sub_links_with_prices