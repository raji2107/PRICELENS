import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


# =================================
# COMMON HEADERS
# =================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}


# =================================
# PRICE EXTRACTION
# =================================

def extract_price(price_text):

    if not price_text:
        return None

    price_match = re.search(
        r"[\d,]+(?:\.\d+)?",
        price_text
    )

    if not price_match:
        return None

    try:
        return float(
            price_match.group()
            .replace(",", "")
        )
    except ValueError:
        return None


# =================================
# CROMA SCRAPER
# =================================

def scrape_croma(url, response):

    print()
    print("================================")
    print("🟢 Croma detected")
    print("================================")

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # PRODUCT NAME

    product_name = None

    name_match = re.search(
        r'"name"\s*:\s*"([^"]+)"',
        response.text,
        re.I
    )

    if name_match:

        product_name = (
            name_match.group(1)
            .replace('\\"', '"')
        )

    if not product_name and soup.title:

        product_name = soup.title.get_text(
            strip=True
        )

        product_name = re.sub(
            r"\s+Online\s*-\s*Croma$",
            "",
            product_name,
            flags=re.I
        )

    if not product_name:

        print(
            "❌ Croma product name not found"
        )

        return None

    # PRODUCT PRICE

    price = None

    price_match = re.search(
        r'"price"\s*:\s*"?([\d,.]+)"?',
        response.text,
        re.I
    )

    if price_match:

        price = extract_price(
            price_match.group(1)
        )

    if price is None:

        print(
            "❌ Croma product price not found"
        )

        return None

    # PRODUCT IMAGE

    image = None

    image_selectors = [
        'meta[property="og:image"]',
        'meta[name="twitter:image"]',
        'img[src]'
    ]

    for selector in image_selectors:

        image_tag = soup.select_one(
            selector
        )

        if image_tag:

            image = (
                image_tag.get("content")
                or image_tag.get("src")
            )

            if image:

                image = urljoin(
                    url,
                    image
                )

                break

    print()
    print("================================")
    print("🎉 Croma scraping successful!")
    print("================================")

    print(
        "Product Name:",
        product_name
    )

    print(
        "Price:",
        price
    )

    print(
        "Image:",
        image
    )

    return {
        "name": product_name,
        "price": price,
        "image": image
    }


# =================================
# RELIANCE DIGITAL SCRAPER
# =================================

def scrape_reliance_digital(url, response):

    print()
    print("================================")
    print("🔵 Reliance Digital detected")
    print("================================")

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # PRODUCT NAME
    # Reliance page title contains
    # the actual product name.

    product_name = None

    if soup.title:

        product_name = soup.title.get_text(
            strip=True
        )

        product_name = re.sub(
            r"\s+at\s+Reliance\s+Digital$",
            "",
            product_name,
            flags=re.I
        )

        product_name = re.sub(
            r"^Buy\s+",
            "",
            product_name,
            flags=re.I
        )

    if not product_name:

        print(
            "❌ Reliance Digital product "
            "name not found"
        )

        return None

    # PRODUCT PRICE

    price = None

    price_match = re.search(
        r'"price"\s*:\s*"?([\d,.]+)"?',
        response.text,
        re.I
    )

    if price_match:

        price = extract_price(
            price_match.group(1)
        )

    if price is None:

        print(
            "❌ Reliance Digital product "
            "price not found"
        )

        return None

    # PRODUCT IMAGE

    image = None

    image_match = re.search(
        r'"image"\s*:\s*"([^"]+)"',
        response.text,
        re.I
    )

    if image_match:

        image = (
            image_match.group(1)
            .replace("\\/", "/")
            .replace('\\"', '"')
        )

        image = urljoin(
            url,
            image
        )

    if not image:

        image_tag = soup.select_one(
            'meta[property="og:image"]'
        )

        if image_tag:

            image = image_tag.get(
                "content"
            )

            if image:

                image = urljoin(
                    url,
                    image
                )

    print()
    print("================================")
    print(
        "🎉 Reliance Digital scraping "
        "successful!"
    )
    print("================================")

    print(
        "Product Name:",
        product_name
    )

    print(
        "Price:",
        price
    )

    print(
        "Image:",
        image
    )

    return {
        "name": product_name,
        "price": price,
        "image": image
    }


# =================================
# CURRENT WEBSCRAPER
# =================================

def scrape_webscraper(url, response):

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    product = soup.select_one(
        ".thumbnail"
    )

    if not product:

        print("❌ Product not found")

        return None

    # PRODUCT NAME

    name_tag = product.select_one(
        ".title"
    )

    if name_tag:

        product_name = (
            name_tag.get("title")
            or name_tag.get_text(
                strip=True
            )
        )

    else:

        product_name = None

    if not product_name:

        print(
            "❌ Product name could not "
            "be extracted"
        )

        return None

    # PRODUCT PRICE

    price_tag = product.select_one(
        ".price"
    )

    if not price_tag:

        print(
            "❌ Product price could not "
            "be extracted"
        )

        return None

    price = extract_price(
        price_tag.get_text(
            strip=True
        )
    )

    if price is None:

        print(
            "❌ Invalid product price"
        )

        return None

    # PRODUCT IMAGE

    image_tag = product.select_one(
        "img"
    )

    image = None

    if image_tag:

        image = image_tag.get("src")

        if image:

            image = urljoin(
                url,
                image
            )

    print()
    print("================================")
    print("🎉 WebScraper successful!")
    print("================================")

    print(
        "Product Name:",
        product_name
    )

    print(
        "Price:",
        price
    )

    print(
        "Image:",
        image
    )

    return {
        "name": product_name,
        "price": price,
        "image": image
    }


# =================================
# MAIN SCRAPER
# =================================

def scrape_product(url):

    print()
    print("================================")
    print("PriceLens Scraper")
    print("================================")

    print(
        "URL:",
        url
    )

    # WEBSITE DETECTION

    url_lower = url.lower()

    if "croma.com" in url_lower:

        website = "croma"

    elif "reliancedigital.in" in url_lower:

        website = "reliance_digital"

    else:

        website = "webscraper"

    print(
        "Detected Website:",
        website
    )

    # REQUEST

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        print(
            "Response Status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "❌ Unable to access webpage. "
                f"Status: {response.status_code}"
            )

            return None

    except requests.RequestException as e:

        print(
            "❌ Request error:",
            e
        )

        return None

    # SELECT SCRAPER

    if website == "croma":

        return scrape_croma(
            url,
            response
        )

    elif website == "reliance_digital":

        return scrape_reliance_digital(
            url,
            response
        )

    return scrape_webscraper(
        url,
        response
    )