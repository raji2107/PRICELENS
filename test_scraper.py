from scraper.price_scraper import scrape_product


url = "https://webscraper.io/test-sites/e-commerce/static"

product = scrape_product(url)

if product:
    print("\n🎉 Scraping successful!")
    print("Product Name:", product["product_name"])
    print("Price:", product["price"])
    print("Image:", product["image"])