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

def dedup_key(link: str) -> str:
    """Ключ для дедупликации: протокол + адрес без fragment (#name)"""
    if link.startswith("vmess://"):
        try:
            b64 = link[8:].split("?")[0].split("#")[0]
            data = json.loads(base64.b64decode(b64 + "==").decode(errors='ignore'))
            key_data = {k: v for k, v in data.items() if k not in ("ps", "remark")}
            return "vmess://" + json.dumps(key_data, sort_keys=True)
        except:
            pass
    return link.split("#")[0]

def is_russian_server(name: str) -> bool:
    """Точная проверка по целым словам"""
    if not name:
        return False
    text = name.upper()
    ru_patterns = [
        r'\bRU\b',
        r'\bRUSSIA\b',
        r'\bРОССИЯ\b',
        r'\bРФ\b',
        r'\bRUSSIAN\b',
        r'\bМОСКВА\b',
        r'\bПИТЕР\b',
        r'\bSPB\b',
        r'\bMSK\b',
        r'\bЕКБ\b',
    ]
    exclude_patterns = [
        r'\bUNBLOCKRU\b',
        r'\bYOUTUBEUNBLOCKRU\b',
        r'\bTG:\s*@',
        r'\bTELEGRAM\b',
    ]
    for pattern in exclude_patterns:
        if re.search(pattern, text):
            return False
    for pattern in ru_patterns:
        if re.search(pattern, text):
            return True
    return False

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

    all_links = {}  # dedup_key -> полная ссылка

    sources = [line.strip() for line in Path("sources.txt").read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.startswith("#")]

    for item in sources:
        print(f"→ {item[:90]}{'...' if len(item)>90 else ''}")
        if is_proxy_link(item):
            key = dedup_key(item)
            if key not in all_links:
                all_links[key] = item
        elif is_subscription_url(item):
            content = fetch_with_retry(item)
            if content:
                valid = [l for l in clean_content(content) if is_proxy_link(l)]
                added = 0
                for l in valid:
                    key = dedup_key(l)
                    if key not in all_links:
                        all_links[key] = l
                        added += 1
                print(f"  ✅ {added} новых ссылок (из {len(valid)} полученных)")

    print(f"\n📊 Всего уникальных ссылок: {len(all_links)}")
    print("🧪 Проверка серверов...")

    ru_links = []
    not_ru_links = []

    for i, link in enumerate(all_links.values()):
        print(f"[{i+1}/{len(all_links)}] Проверка...", end="\r")
        if tcp_test(link):
            name_part = link.split("#")[-1] if "#" in link else link
            if is_russian_server(name_part):
                ru_links.append(link)
            else:
                not_ru_links.append(link)

    with open("subs/all_ru.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(ru_links))

    with open("subs/all_not_ru.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(not_ru_links))

    print(f"\n🎉 Готово!")
    print(f"  🇷🇺 all_ru.txt → {len(ru_links)} серверов")
    print(f"  🌍 all_not_ru.txt → {len(not_ru_links)} серверов")

if __name__ == "__main__":
    main()
