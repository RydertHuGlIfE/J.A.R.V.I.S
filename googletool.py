import os
import requests
from bs4 import BeautifulSoup

def google_res(query):
    url = "https://html.duckduckgo.com/html/"
    payload = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
    }
    
    proxy_str = os.environ.get("DDGS_PROXY")
    proxies = {"http": proxy_str, "https": proxy_str} if proxy_str else None
    
    try:
        response = requests.post(url, data=payload, headers=headers, proxies=proxies, timeout=10)
        if response.status_code != 200:
            print(f"Search error: Status {response.status_code}")
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
        print(f"Connection error: {e}")
        return []

if __name__ == "__main__":
    print(google_res("latest linkin park concert"))