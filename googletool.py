import os
import requests
from bs4 import BeautifulSoup

import urllib.parse

def decode_yahoo_url(url):
    if not url:
        return ""
    if "RU=" in url:
        try:
            parts = url.split("RU=")
            real_url = parts[1].split("/RK=")[0]
            return urllib.parse.unquote(real_url)
        except Exception:
            pass
    return url

def extract_ticker(url):
    # Google Finance format: https://www.google.com/finance/quote/IDEA:NSE
    if "google.com/finance" in url:
        try:
            parts = url.split("/quote/")
            if len(parts) > 1:
                ticker_exchange = parts[1].split("?")[0].split("/")[0]
                if ":" in ticker_exchange:
                    ticker, exchange = ticker_exchange.split(":")
                    if exchange == "NSE":
                        return f"{ticker}.NS"
                    elif exchange == "BSE":
                        return f"{ticker}.BO"
                    elif exchange == "LON":
                        return f"{ticker}.L"
                    elif exchange in ["NASDAQ", "NYSE"]:
                        return ticker
                    return ticker
        except Exception:
            pass
    # Yahoo Finance format: https://finance.yahoo.com/quote/IDEA.NS
    elif "finance.yahoo.com/quote/" in url:
        try:
            parts = url.split("/quote/")
            if len(parts) > 1:
                return parts[1].split("?")[0].split("/")[0]
        except Exception:
            pass
    return None

def fetch_live_yahoo_price(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            prev_close = meta.get("chartPreviousClose")
            currency = meta.get("currency", "")
            symbol = meta.get("symbol", ticker)
            
            if price is not None:
                change_str = ""
                if prev_close is not None and prev_close != 0:
                    change = price - prev_close
                    pct = (change / prev_close) * 100
                    sign = "+" if change >= 0 else ""
                    change_str = f" ({sign}{change:.2f}, {sign}{pct:.2f}%)"
                
                currency_symbol = currency
                if currency == "INR":
                    currency_symbol = "₹"
                elif currency == "USD":
                    currency_symbol = "$"
                elif currency == "GBp":
                    currency_symbol = "GBX"
                    
                return {
                    "title": f"LIVE: {symbol} Stock Price (Real-Time)",
                    "url": f"https://finance.yahoo.com/quote/{symbol}",
                    "description": f"Current Real-Time Price: {currency_symbol}{price}{change_str} as of today. (Direct API Quote)"
                }
    except Exception as e:
        pass
    return None

def google_res(query):
    # Primary search: Yahoo (does not require Captcha verification)
    yahoo_url = "https://search.yahoo.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    params = {"p": query}
    
    try:
        response = requests.get(yahoo_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            unique_results = []
            divs = soup.find_all("div", class_="algo")
            
            # Check for live stock price tickers first
            live_quotes = []
            
            for div in divs:
                # Find the main result link (usually the first anchor tag)
                link = div.find("a")
                desc_div = div.find("div", class_="compText") or div.find("span", class_="compDscr") or div.find("p")
                
                if link:
                    title = link.get_text(strip=True)
                    href = link.get("href")
                    desc = desc_div.get_text(strip=True) if desc_div else ""
                    
                    clean_href = decode_yahoo_url(href)
                    ticker = extract_ticker(clean_href)
                    
                    # If this is a stock url, fetch live quote
                    if ticker:
                        live_quote = fetch_live_yahoo_price(ticker)
                        if live_quote and live_quote["url"] not in [q["url"] for q in live_quotes]:
                            live_quotes.append(live_quote)
                    
                    # Ignore internal Yahoo links
                    if href and not href.startswith("https://r.search.yahoo.com/_ylt=") and not href.startswith("http://r.search.yahoo.com/"):
                        unique_results.append({
                            "title": title,
                            "url": clean_href,
                            "description": desc
                        })
                    elif href:
                        unique_results.append({
                            "title": title,
                            "url": clean_href,
                            "description": desc
                        })
            
            # Prepend live stock quotes to search results
            if live_quotes:
                unique_results = live_quotes + unique_results
                
            if unique_results:
                return unique_results[:15]
    except Exception as e:
        print(f"Yahoo search error: {e}")

    # Fallback search 2: Mojeek (very friendly to scrapers, no trackers/captchas)
    mojeek_url = "https://www.mojeek.com/search"
    try:
        response = requests.get(mojeek_url, params={"q": query}, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            unique_results = []
            for a in soup.find_all("a", class_="title"):
                title = a.text.strip()
                href = a.get("href")
                
                # Find parent container
                li = a.find_parent("li")
                desc = ""
                if li:
                    p_tags = li.find_all("p")
                    for p in p_tags:
                        p_text = p.text.strip()
                        if p_text and not p_text.startswith("http") and "›" not in p_text and not p_text.startswith("See more results"):
                            desc = p_text
                            break
                            
                if href and not href.startswith("/"):
                    unique_results.append({
                        "title": title,
                        "url": href,
                        "description": desc
                    })
            if unique_results:
                return unique_results[:15]
    except Exception as e:
        print(f"Mojeek search error: {e}")

    # Fallback search 4: DuckDuckGo
    ddg_url = "https://html.duckduckgo.com/html/"
    payload = {"q": query}
    
    proxy_str = os.environ.get("DDGS_PROXY")
    proxies = {"http": proxy_str, "https": proxy_str} if proxy_str else None
    
    try:
        response = requests.post(ddg_url, data=payload, headers=headers, proxies=proxies, timeout=10)
        if response.status_code != 200:
            print(f"DuckDuckGo Search error: Status {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        unique_results = []
        
        for r in soup.find_all("div", class_="result"):
            title_tag = r.find("a", class_="result__url")
            snippet_tag = r.find("a", class_="result__snippet")
            
            if title_tag:
                title = title_tag.get_text(strip=True)
                href = title_tag.get("href")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                
                if href and not href.startswith("//duckduckgo.com") and not href.startswith("https://duckduckgo.com"):
                    unique_results.append({
                        "title": title,
                        "url": href,
                        "description": snippet
                    })
                    
        return unique_results[:15]
        
    except Exception as e:
        print(f"DuckDuckGo connection error: {e}")
        return []

import sys
from datetime import date

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw_query = " ".join(sys.argv[1:])
        today_date = date.today().strftime("%B %d, %Y")
        query = f"{raw_query} {today_date}"
        print(f"Actual Search Query: '{query}'")
        
        results = google_res(query)
        if not results:
            print("No results found or rate limited.")
        else:
            for r in results:
                print(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['description']}\n---")
    else:
        print("Usage: python3 googletool.py <query>")