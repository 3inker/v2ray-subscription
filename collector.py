import requests
import re
import time
import socket
import json
import base64
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse
from datetime import datetime

# ================= НАСТРОЙКИ =================
TIMEOUT = 10
DELAY = 0.15
MAX_RETRIES = 3
IP_CHECK_ATTEMPTS = 2
# ============================================

def get_ip_info(server):
    """Много API для определения страны и провайдера"""
    apis = [
        f"http://ip-api.com/json/{server}?fields=countryCode,org,isp",
        f"https://ipwho.is/{server}",
        f"https://api.ipapi.is/?q={server}",
        f"https://api.beacondb.net/v1/ip/{server}",
        f"https://freeipapi.com/api/json/{server}",
        f"https://api.iplocate.io/api/lookup/{server}",
    ]
    
    for api_url in apis:
        try:
            r = requests.get(api_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                continue
            data = r.json()

            if "countryCode" in data:
                country = data.get("countryCode")
                provider = data.get("org") or data.get("isp") or "Unknown"
            elif "country_code" in data:
                country = data.get("country_code")
                provider = data.get("isp") or data.get("connection", {}).get("isp") or "Unknown"
            elif "country" in data:
                country = data.get("country", {}).get("code") if isinstance(data.get("country"), dict) else data.get("country")
                provider = data.get("isp") or data.get("org") or "Unknown"
            else:
                continue

            if country and len(str(country)) == 2:
                provider = str(provider).strip()[:40] or "Unknown"
                return country.upper(), provider
        except:
            continue
    
    return "Unknown", "Unknown"


def is_subscription_url(text: str) -> bool:
    return text.startswith(("http://", "https://"))

def is_proxy_link(text: str) -> bool:
    return any(text.startswith(p) for p in ["vless://", "vmess://", "trojan://", "ss://", "hysteria2://", "hy2://"])

def fetch_with_retry(url):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text
        except:
            time.sleep(2 ** attempt)
    return None

def clean_content(content):
    return [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

def get_server_address(link):
    try:
        if link.startswith("vmess://"):
            b64 = link[8:].split("?")[0].split("#")[0]
            data = json.loads(base64.b64decode(b64 + "==").decode(errors='ignore'))
            return data.get("add") or data.get("address"), int(data.get("port", 443))
        
        clean_link = link.split("?")[0]
        parsed = urlparse(clean_link)
        addr = parsed.hostname
        port = parsed.port or 443
        if not addr and "@" in clean_link:
            addr = clean_link.split("@")[1].split(":")[0].split("/")[0]
        return addr, port
    except:
        return None, 443

def tcp_test(link):
    for _ in range(IP_CHECK_ATTEMPTS):
        server, port = get_server_address(link)
        if not server:
            return False, 9999
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            start = time.time()
            result = sock.connect_ex((server, port))
            sock.close()
            if result == 0:
                return True, 0
        except:
            time.sleep(0.5)
    return False, 9999

def main():
    Path("subs").mkdir(exist_ok=True)

    print("🔄 Собираем источники...")
    all_links = set()

    sources = [line.strip() for line in Path("sources.txt").read_text(encoding="utf-8").splitlines() 
               if line.strip() and not line.startswith("#")]

    for item in sources:
        print(f"→ {item[:85]}{'...' if len(item)>85 else ''}")
        if is_proxy_link(item):
            all_links.add(item)
        elif is_subscription_url(item):
            content = fetch_with_retry(item)
            if content:
                valid = [l for l in clean_content(content) if is_proxy_link(l)]
                all_links.update(valid)
                print(f"   ✅ {len(valid)} ссылок")

    print(f"\n📊 Всего уникальных ссылок: {len(all_links)}")

    # Проверка
    print("🧪 Проверка серверов...")
    working = defaultdict(list)   # country -> list of (link, provider)

    for i, link in enumerate(all_links):
        print(f"[{i+1}/{len(all_links)}] Проверка...", end="\r")
        
        ok, _ = tcp_test(link)
        if ok:
            server, _ = get_server_address(link)
            country, provider = get_ip_info(server) if server else ("Unknown", "Unknown")
            working[country].append((link, provider))
        
        time.sleep(DELAY)

    # Сортировка по стране (алфавит)
    ru_links = []
    not_ru_links = []

    # Обработка RU
    if "RU" in working:
        items = working.pop("RU")
        for num, (link, provider) in enumerate(items, 1):
            name = f"🇷🇺 Russia [{num}] | {provider}"
            new_link = link.rsplit("#", 1)[0] + f"#{name}" if "#" in link else f"{link}#{name}"
            ru_links.append(new_link)

    # Обработка остальных стран (сортировка по алфавиту)
    for country in sorted(working.keys()):   # <-- Сортировка по алфавиту
        items = working[country]
        for num, (link, provider) in enumerate(items, 1):
            flag = "🇷🇺" if country == "RU" else "🌍"
            country_name = "Russia" if country == "RU" else country
            name = f"{flag} {country_name} [{num}] | {provider}"
            new_link = link.rsplit("#", 1)[0] + f"#{name}" if "#" in link else f"{link}#{name}"
            not_ru_links.append(new_link)

    # Сохранение
    with open("subs/all_ru.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(ru_links))
    
    with open("subs/all_not_ru.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(not_ru_links))

    total = len(ru_links) + len(not_ru_links)
    print(f"\n🎉 Готово!")
    print(f"   🇷🇺 RU: {len(ru_links)}")
    print(f"   🌍 Не RU: {len(not_ru_links)}")
    print(f"   Всего: {total}")

if __name__ == "__main__":
    main()