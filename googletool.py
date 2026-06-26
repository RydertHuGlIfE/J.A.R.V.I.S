import os
import requests
from bs4 import BeautifulSoup

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
            for div in divs:
                # Find the main result link (usually the first anchor tag)
                link = div.find("a")
                desc_div = div.find("div", class_="compText") or div.find("span", class_="compDscr") or div.find("p")
                
                if link:
                    title = link.get_text(strip=True)
                    href = link.get("href")
                    desc = desc_div.get_text(strip=True) if desc_div else ""
                    
                    # Ignore internal Yahoo links
                    if href and not href.startswith("https://r.search.yahoo.com/_ylt=") and not href.startswith("http://r.search.yahoo.com/"):
                        unique_results.append({
                            "title": title,
                            "url": href,
                            "description": desc
                        })
                    elif href:
                        unique_results.append({
                            "title": title,
                            "url": href,
                            "description": desc
                        })
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
        
        results = google_res(query)
        if not results:
            print("No results found or rate limited.")
        else:
            for r in results:
                print(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['description']}\n---")
    else:
        print("Usage: python3 googletool.py <query>")