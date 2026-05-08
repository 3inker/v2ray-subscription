import requests
import re
import time
import socket
import json
import base64
from pathlib import Path
from urllib.parse import urlparse

# ================= НАСТРОЙКИ =================
TIMEOUT = 10
DELAY = 0.12
MAX_RETRIES = 3
IP_CHECK_ATTEMPTS = 2
# ============================================

def is_russian_in_name(name: str) -> bool:
    """Определяем российский сервер по названию"""
    if not name:
        return False
    text = name.upper()
    russian_keywords = ["RU", "RUSSIA", "РОССИЯ", "РФ", "RUSSIAN", "МОСКВА", "САНКТ", "ЕКБ", "SPB", "MSK"]
    return any(kw in text for kw in russian_keywords)

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
    """Проверка с несколькими попытками"""
    for _ in range(IP_CHECK_ATTEMPTS):
        server, port = get_server_address(link)
        if not server:
            return False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            result = sock.connect_ex((server, port))
            sock.close()
            if result == 0:
                return True
        except:
            time.sleep(0.5)
    return False

def main():
    Path("subs").mkdir(exist_ok=True)

    print("🔄 Собираем источники...")
    all_links = set()

    sources = [line.strip() for line in Path("sources.txt").read_text(encoding="utf-8").splitlines() 
               if line.strip() and not line.startswith("#")]

    for item in sources:
        print(f"→ {item[:90]}{'...' if len(item)>90 else ''}")
        if is_proxy_link(item):
            all_links.add(item)
        elif is_subscription_url(item):
            content = fetch_with_retry(item)
            if content:
                valid = [l for l in clean_content(content) if is_proxy_link(l)]
                all_links.update(valid)
                print(f"   ✅ {len(valid)} ссылок")

    print(f"\n📊 Всего уникальных ссылок: {len(all_links)}")

    print("🧪 Проверка серверов...")
    ru_links = []
    not_ru_links = []

    for i, link in enumerate(all_links):
        print(f"[{i+1}/{len(all_links)}] Проверка...", end="\r")
        
        if tcp_test(link):
            # Берём оригинальное название (после #)
            name_part = link.split("#")[-1] if "#" in link else ""
            
            if is_russian_in_name(name_part):
                ru_links.append(link)
            else:
                not_ru_links.append(link)

    # Сохраняем без изменения названий
    with open("subs/all_ru.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(ru_links))
    
    with open("subs/all_not_ru.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(not_ru_links))

    print(f"\n🎉 Готово!")
    print(f"   🇷🇺 all_ru.txt     → {len(ru_links)} серверов")
    print(f"   🌍 all_not_ru.txt → {len(not_ru_links)} серверов")
    print(f"   Всего рабочих: {len(ru_links) + len(not_ru_links)}")

if __name__ == "__main__":
    main()