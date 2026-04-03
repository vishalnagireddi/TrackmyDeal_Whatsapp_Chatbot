import json
import re
import time
import random
from curl_cffi import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

def clean_price(price_str):
    if not price_str:
        return None
    price_str = re.sub(r'[^\d.]', '', price_str)
    try:
        if price_str.endswith('.'):
             price_str = price_str[:-1]
        return float(price_str)
    except ValueError:
        return None

def extract_from_json_ld(soup):
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            
            # Handle list of JSON objects
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') in ['Product', 'ProductGroup']:
                        return extract_product_from_json_ld(item)
            elif data.get('@type') in ['Product', 'ProductGroup']:
                return extract_product_from_json_ld(data)
                
            # Handle cases where product is wrapped in Graph
            if '@graph' in data:
                for item in data['@graph']:
                    if item.get('@type') == 'Product':
                         return extract_product_from_json_ld(item)
        except (json.JSONDecodeError, TypeError):
            continue
    return None

def extract_product_from_json_ld(data):
    title = data.get('name')
    image = data.get('image')
    if isinstance(image, list) and len(image) > 0:
        image = image[0]
        
    price = None
    offers = data.get('offers')
    if offers:
         if isinstance(offers, list) and len(offers) > 0:
             price = offers[0].get('price')
         elif isinstance(offers, dict):
             price = offers.get('price')
             if not price and offers.get('lowPrice'):
                  price = offers.get('lowPrice')
    
    return {
        "title": title,
        "price": clean_price(str(price)) if price else None,
        "image": image if isinstance(image, str) else None
    }

def extract_from_meta_tags(soup):
    title = None
    image = None
    price = None
    
    # OpenGraph tags
    og_title = soup.find("meta", property="og:title")
    if og_title: title = og_title.get("content")
    
    og_image = soup.find("meta", property="og:image")
    if og_image: image = og_image.get("content")
    
    # Standard Price Meta Tags
    meta_price = soup.find("meta", property="product:price:amount")
    if meta_price: price = meta_price.get("content")
    
    if not price:
        meta_price = soup.find("meta", itemprop="price")
        if meta_price: price = meta_price.get("content")
        
    return {
        "title": title,
        "price": clean_price(str(price)) if price else None,
        "image": image
    }

def extract_from_custom_spas(html, url):
    """Deep extracts price from raw React Hydration internal states to bypass Playwright needs."""
    title = None
    price = None
    
    if "myntra.com" in url:
        price_match = re.search(r'"discounted"\s*:\s*(\d+)', html)
        if not price_match:
             price_match = re.search(r'"mrp"\s*:\s*(\d+)', html)
        if price_match:
             price = clean_price(price_match.group(1))
        title_match = re.search(r'"name"\s*:\s*"([^"]+)"', html)
        if title_match: title = title_match.group(1)

    elif "nykaa.com" in url:
        price_match = re.search(r'"discountedPrice"\s*:\s*([\d.]+)', html)
        if price_match:
             price = clean_price(price_match.group(1))
             
    if price:
        return {"title": title, "price": price, "image": None}
    return None

def extract_from_common_selectors(soup):
    # Try common price classes
    price_selectors = [
        '.a-price-whole', '#priceblock_ourprice', '.a-offscreen',  # Amazon
        '.Nx9bqj', '.hl05eU',  # Flipkart
        '[data-price]', '.price', '.product-price', '.current-price' # Generic
    ]
    price = None
    for selector in price_selectors:
        el = soup.select(selector)
        if el and el[0].text:
             price = clean_price(el[0].text)
             if price: break
             
    title_selectors = ['#productTitle', '.VU-Tz5', 'h1']
    title = None
    for selector in title_selectors:
        el = soup.select(selector)
        if el and el[0].text:
             title = el[0].text.strip()
             break
             
    return {
        "title": title,
        "price": price,
        "image": None
    }

def scrape_with_requests(url):
    # Spoof the TLS fingerprint of Google Chrome to completely bypass Akamai/Datadome
    # Spoof the TLS fingerprint of Google Chrome to completely bypass Akamai/Datadome
    response = requests.get(url, headers=get_headers(), impersonate="chrome110", timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    product_data = {"url": url, "title": None, "price": None, "image": None}
    
    # Strategy 1: JSON-LD
    json_ld_data = extract_from_json_ld(soup)
    if json_ld_data and json_ld_data['price']:
        product_data.update({k: v for k, v in json_ld_data.items() if v is not None})
        return product_data
        
    # Strategy 2: Meta Tags
    meta_data = extract_from_meta_tags(soup)
    if meta_data and meta_data['price']:
        product_data.update({k: v for k, v in meta_data.items() if v is not None})
        return product_data
        
    # Strategy 3: Custom SPA State Extractors (Myntra/Ajio)
    spa_data = extract_from_custom_spas(response.text, url)
    if spa_data and spa_data['price']:
         product_data.update({k: v for k, v in spa_data.items() if v is not None})
         return product_data
         
    # Strategy 4: Common Selectors
    selector_data = extract_from_common_selectors(soup)
    if selector_data and selector_data['price']:
         product_data.update({k: v for k, v in selector_data.items() if v is not None})
         
    return product_data

def scrape_with_playwright(url):
    product_data = {"url": url, "title": None, "price": None, "image": None}
    try:
        with sync_playwright() as p:
            # Firefox is often less detected by Akamai/Datadome than Chromium
            browser = p.firefox.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
                viewport={'width': 1920, 'height': 1080},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                }
            )
            
            page = context.new_page()
            
            # Add early random jitter to avoid fingerprinting timing patterns
            jitter = random.uniform(1.0, 3.0)
            page.wait_for_timeout(int(jitter * 1000))
            
            # Navigate and wait for networking to settle
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            
            # Wait for common price selectors to appear (Amazon specific)
            try:
                page.wait_for_selector(".a-price-whole", timeout=8000)
            except:
                pass # Continue to generic extraction if not found
            
            # Scroll down to trigger lazy loading and wait with random jitter
            page.evaluate("window.scrollTo(0, 500)")
            post_scroll_jitter = random.uniform(2.5, 4.5)
            page.wait_for_timeout(int(post_scroll_jitter * 1000))
            
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Same strategies as above
            json_ld_data = extract_from_json_ld(soup)
            if json_ld_data and json_ld_data['price']:
                product_data.update({k: v for k, v in json_ld_data.items() if v is not None})
            else:
                meta_data = extract_from_meta_tags(soup)
                if meta_data and meta_data['price']:
                    product_data.update({k: v for k, v in meta_data.items() if v is not None})
                else:
                    selector_data = extract_from_common_selectors(soup)
                    if selector_data and selector_data['price']:
                        product_data.update({k: v for k, v in selector_data.items() if v is not None})
                        
            browser.close()
    except Exception as e:
        error_msg = str(e).encode('ascii', 'ignore').decode()
        print(f"Playwright scraping failed for {url}: {error_msg}")
        
    return product_data

def scrape_product(url):
    """
    Main entry point for scraping.
    Attempts requests first, falls back to Playwright if requests fails or returns no price.
    """
    try:
        data = scrape_with_requests(url)
        if data.get('price'):
            print("Successfully scraped with requests.")
            return data
    except Exception as e:
         error_msg = str(e).encode('ascii', 'ignore').decode()
         print(f"Requests scraping failed for {url}: {error_msg}")
         
    print("Falling back to Playwright scraping...")
    return scrape_with_playwright(url)

if __name__ == "__main__":
    # Test
    test_url = "https://www.amazon.in/dp/B0CHX1W1XY"
    print(scrape_product(test_url))
