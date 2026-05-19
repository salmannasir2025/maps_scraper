import re
import time
import urllib.parse
import logging
from bs4 import BeautifulSoup
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# User-Agent list to rotate or use a premium one for website scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def extract_emails_from_url(url, timeout=5):
    """
    Fetches the website HTML and extracts matching email addresses using regex.
    Filters out common false positives like image extensions or static files.
    """
    if not url:
        return ""
    
    # Standardize URL
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
        
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True, verify=False)
        if response.status_code != 200:
            return ""
        
        # Extract emails using regex
        text = response.text
        # Regex for standard emails
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
        raw_emails = re.findall(email_pattern, text)
        
        # Clean and filter
        valid_emails = set()
        invalid_extensions = {
            "png", "jpg", "jpeg", "gif", "svg", "webp", "pdf", "zip", 
            "gz", "css", "js", "woff", "woff2", "mp4", "mp3", "tiff", 
            "bmp", "ico", "exe", "xml"
        }
        
        for email in raw_emails:
            email_lower = email.lower()
            # Basic validation
            parts = email_lower.split(".")
            if len(parts) > 1 and parts[-1] not in invalid_extensions:
                # Avoid wix / wordpress theme defaults
                if "domain.com" not in email_lower and "email.com" not in email_lower:
                    valid_emails.add(email)
                    
        return ", ".join(valid_emails) if valid_emails else ""
    except Exception as e:
        logger.error(f"Error extracting emails from {url}: {e}")
        return ""

def init_driver(headless=True):
    """
    Initializes a highly optimized Selenium Chrome Webdriver.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1200,800")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--lang=en-US")
    # Add fake headers/user agent to Selenium
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Hide automation indicators
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def scrape_google_maps(keyword, city, state, country, limit=10, phone_only=False, website_only=False, email_enrich=False):
    """
    Scrapes Google Maps business listings. 
    Yields intermediate status dicts for progress tracking in Streamlit.
    """
    query = f"{keyword} in {city}, {state}, {country}"
    search_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(query)}"
    
    yield {"status": "info", "message": f"Initializing browser for '{query}'..."}
    driver = None
    
    try:
        driver = init_driver(headless=True)
        driver.get(search_url)
        time.sleep(4)
        
        # Check if Google Maps redirected straight to a single business page instead of search results list
        current_url = driver.current_url
        if "/maps/place/" in current_url:
            yield {"status": "info", "message": "Direct match found. Scraping details..."}
            business = extract_single_business_details(driver)
            if business:
                # Post-processing
                if phone_only and not business.get("phone"):
                    yield {"status": "done", "results": []}
                    return
                if website_only and not business.get("website"):
                    yield {"status": "done", "results": []}
                    return
                if email_enrich and business.get("website"):
                    yield {"status": "info", "message": f"Enriching email for {business['name']}..."}
                    business["email"] = extract_emails_from_url(business["website"])
                
                yield {"status": "progress", "count": 1, "total": 1, "business": business}
                yield {"status": "done", "results": [business]}
            else:
                yield {"status": "done", "results": []}
            return

        # Regular list view flow
        yield {"status": "info", "message": "Loading search results..."}
        
        # Scroll the left pane (role="feed") to load matching cards
        feed_selector = "div[role='feed']"
        try:
            feed = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, feed_selector))
            )
        except Exception:
            # Fallback if the feed has a different role/selector
            feed = None
            logger.warning("Could not find div[role='feed']. Scanning DOM alternative...")
            
        if not feed:
            # Try alternative: get elements by class name or tag name that resembles feed
            try:
                feed = driver.find_element(By.XPATH, "//div[contains(@aria-label, 'Results for')]")
            except Exception:
                yield {"status": "error", "message": "Search results container not found. Check search terms."}
                return

        # Scrolling feed logic
        listings_urls = []
        last_height = driver.execute_script("return arguments[0].scrollHeight", feed)
        no_new_items_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 40
        
        yield {"status": "info", "message": "Scrolling to discover businesses..."}
        
        while len(listings_urls) < limit and scroll_attempts < max_scroll_attempts:
            # Scroll down
            driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", feed)
            time.sleep(2.0)
            
            # Find all card links
            cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
            urls = []
            for card in cards:
                href = card.get_attribute("href")
                if href and href not in urls:
                    urls.append(href)
            
            listings_urls = urls[:limit]
            
            new_height = driver.execute_script("return arguments[0].scrollHeight", feed)
            if new_height == last_height:
                no_new_items_count += 1
                # Try to scroll up a tiny bit then down to trigger lazy load
                if no_new_items_count >= 3:
                    driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight - 500);", feed)
                    time.sleep(1.0)
                    driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", feed)
                    time.sleep(2.0)
                    new_height = driver.execute_script("return arguments[0].scrollHeight", feed)
                    if new_height == last_height:
                        logger.info("Reached bottom of feed.")
                        break
                    no_new_items_count = 0
            else:
                no_new_items_count = 0
                
            last_height = new_height
            scroll_attempts += 1
            yield {"status": "scroll", "discovered": len(listings_urls), "limit": limit}

        total_discovered = len(listings_urls)
        yield {"status": "info", "message": f"Discovered {total_discovered} businesses. Starting details extraction..."}
        
        results = []
        for i, url in enumerate(listings_urls):
            yield {"status": "info", "message": f"Extracting [{i+1}/{total_discovered}]: Navigating to details page..."}
            driver.get(url)
            time.sleep(2.5)  # Wait for panel to load details
            
            business = extract_single_business_details(driver)
            if business:
                business["maps_url"] = url
                
                # Check filtering flags early to save time on email extraction
                has_phone = bool(business.get("phone"))
                has_website = bool(business.get("website"))
                
                if phone_only and not has_phone:
                    logger.info(f"Skipping {business['name']} - missing phone.")
                    continue
                if website_only and not has_website:
                    logger.info(f"Skipping {business['name']} - missing website.")
                    continue
                
                # Enrich with email if needed
                if email_enrich and has_website:
                    yield {"status": "info", "message": f"Crawling website for {business['name']}..."}
                    emails = extract_emails_from_url(business["website"])
                    business["email"] = emails
                else:
                    business["email"] = ""
                    
                results.append(business)
                yield {"status": "progress", "count": len(results), "total": total_discovered, "business": business}
            else:
                logger.warning(f"Failed to extract details from {url}")
                
        yield {"status": "done", "results": results}
        
    except Exception as e:
        logger.error(f"Error in scraping pipeline: {e}", exc_info=True)
        yield {"status": "error", "message": f"Scraping error: {str(e)}"}
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Browser session closed.")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

def extract_single_business_details(driver):
    """
    Extracts all fields for the currently loaded business details panel.
    Returns a dictionary of business details.
    """
    try:
        # Title selector
        title_selectors = ["h1.DUwDvf", "h1"]
        title = ""
        for selector in title_selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, selector)
                if el and el.text:
                    title = el.text.strip()
                    break
            except Exception:
                continue
                
        if not title:
            # Try XPath fallback
            try:
                title = driver.find_element(By.XPATH, "//h1").text.strip()
            except Exception:
                return None
                
        # Category
        category = ""
        category_selectors = ["button.DkEaCc", "span.fontBodyMedium"]
        for selector in category_selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in els:
                    if el.text and len(el.text.strip()) > 2 and el.text.strip() not in ["Share", "Save", "Nearby", "Send to phone"]:
                        category = el.text.strip()
                        break
                if category:
                    break
            except Exception:
                continue
                
        # Address
        address = ""
        try:
            addr_el = driver.find_element(By.CSS_SELECTOR, "button[data-item-id='address']")
            address = addr_el.text.strip()
        except Exception:
            # Fallback XPath looking for standard icons/classes
            try:
                address = driver.find_element(By.XPATH, "//button[contains(@data-item-id,'address')]//div[contains(@class,'Io6YTe')]").text.strip()
            except Exception:
                pass
                
        # Phone
        phone = ""
        try:
            phone_el = driver.find_element(By.CSS_SELECTOR, "button[data-item-id^='phone:tel:']")
            # The data-item-id contains the phone, e.g. "phone:tel:+123456789"
            phone_raw = phone_el.get_attribute("data-item-id")
            phone = phone_raw.replace("phone:tel:", "").strip()
        except Exception:
            try:
                phone = driver.find_element(By.XPATH, "//button[contains(@data-item-id,'phone:tel:')]//div[contains(@class,'Io6YTe')]").text.strip()
            except Exception:
                pass
                
        # Website
        website = ""
        try:
            web_el = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
            website = web_el.get_attribute("href")
        except Exception:
            try:
                web_el = driver.find_element(By.XPATH, "//a[contains(@data-item-id,'authority')]")
                website = web_el.get_attribute("href")
            except Exception:
                pass
                
        if website:
            # Strip tracker parameters if any
            parsed_web = urllib.parse.urlparse(website)
            # Remove google redirections
            if "google.com" in parsed_web.netloc and "/url" in parsed_web.path:
                queries = urllib.parse.parse_qs(parsed_web.query)
                if "q" in queries:
                    website = queries["q"][0]
                elif "url" in queries:
                    website = queries["url"][0]
            
            # Final clean
            parsed_clean = urllib.parse.urlparse(website)
            website = f"{parsed_clean.scheme}://{parsed_clean.netloc}{parsed_clean.path}"
            
        # Rating
        rating = ""
        reviews_count = ""
        try:
            # Look inside F7nice
            rating_container = driver.find_element(By.CSS_SELECTOR, "div.F7nice")
            spans = rating_container.find_elements(By.TAG_NAME, "span")
            if len(spans) > 0:
                rating = spans[0].text.strip()
            if len(spans) > 1:
                reviews_count = spans[1].text.strip().replace("(", "").replace(")", "").replace(",", "")
        except Exception:
            pass

        return {
            "name": title,
            "category": category,
            "address": address,
            "phone": phone,
            "website": website,
            "rating": rating,
            "reviews_count": reviews_count,
            "maps_url": driver.current_url
        }
    except Exception as e:
        logger.error(f"Error parsing detail elements: {e}")
        return None
