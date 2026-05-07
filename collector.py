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
TIMEOUT = 8
DELAY = 0.1
MAX_RETRIES = 3
# ============================================

def get_ip_info(server):
    """Несколько API для определения страны и провайдера"""
    apis = [
        f"http://ip-api.com/json/{server}?fields=countryCode,org,isp",
        f"https://ipwho.is/{server}",
        f"https://freeipapi.com/api/json/{server}"
    ]
    
    for api in apis:
        try:
            r = requests.get(api, timeout=7)
            if r.status_code == 200:
                data = r.json()
                
                if "countryCode" in data:
                    country = data.get("countryCode")
                    provider = data.get("org") or data.get("isp") or data.get("ispName") or "Unknown"
                elif "country_code" in data:
                    country = data.get("country_code")
                    provider = data.get("isp") or data.get("connection", {}).get("isp") or "Unknown"
                else:
                    continue
                
                # Упрощаем название провайдера
                for name in ["Cloudflare", "Hetzner", "Aeza", "Contabo", "OVH", "Amazon", "Google", "Oracle", "Yandex"]:
                    if name.lower() in provider.lower():
                        provider = name
                        break
                else:
                    provider = provider.split()[0][:30]
                
                return country, provider
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

def try_decode_base64(text):
    try:
        cleaned = re.sub(r'\s+', '', text.strip())
        padding = len(cleaned) % 4
        if padding:
            cleaned += '=' * (4 - padding)
        decoded = base64.b64decode(cleaned).decode('utf-8')
        if any(x in decoded for x in ["vless://", "vmess://", "trojan://"]):
            return decoded
    except:
        pass
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
    server, port = get_server_address(link)
    if not server:
        return False, 9999
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        start = time.time()
        result = sock.connect_ex((server, port))
        latency = int((time.time() - start) * 1000)
        sock.close()
        return (result == 0), min(latency, 999)
    except:
        return False, 9999

def update_readme_stats(ru_count, not_ru_count, total):
    readme_path = Path("README.md")
    if not readme_path.exists():
        return
    
    content = readme_path.read_text(encoding="utf-8")
    
    content = re.sub(r"\*\*Все RU\*\*\s+\|\s+`\d+`", f"**Все RU**                | `{ru_count}`", content)
    content = re.sub(r"\*\*Все не RU\*\*\s+\|\s+`\d+`", f"**Все не RU**             | `{not_ru_count}`", content)
    content = re.sub(r"\*\*Всего рабочих\*\*\s+\|\s+`\d+`", f"**Всего рабочих**         | `{total}`", content)
    
    content = re.sub(
        r"\*Последнее обновление: .*",
        f"*Последнее обновление: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        content
    )
    
    readme_path.write_text(content, encoding="utf-8")
    print("✅ README.md обновлён")

def main():
    Path("subs").mkdir(exist_ok=True)

    print("🔄 Собираем источники...")
    all_links = set()

    sources = [line.strip() for line in Path("sources.txt").read_text(encoding="utf-8").splitlines() 
               if line.strip() and not line.startswith("#")]

    for item in sources:
        print(f"→ {item[:80]}{'...' if len(item)>80 else ''}")
        if is_proxy_link(item):
            all_links.add(item)
        elif is_subscription_url(item):
            content = fetch_with_retry(item)
            if content:
                decoded = try_decode_base64(content)
                if decoded:
                    content = decoded
                valid = [l for l in clean_content(content) if is_proxy_link(l)]
                all_links.update(valid)
                print(f"   ✅ {len(valid)} ссылок")

    print(f"\n📊 Всего собрано ссылок: {len(all_links)}")

    # Проверка
    print("🧪 Проверка серверов...")
    ru_links = []
    not_ru_links = []

    for i, link in enumerate(all_links):
        print(f"[{i+1}/{len(all_links)}] Проверка...", end="\r")
        ok, ping = tcp_test(link)
        if ok:
            server, _ = get_server_address(link)
            country, provider = get_ip_info(server) if server else ("Unknown", "Unknown")
            
            flag = "🇷🇺" if country.upper() == "RU" else "🌍"
            name = f"{flag} {country} | {provider} | 🫐"
            
            new_link = link.rsplit("#", 1)[0] + "#" + name if "#" in link else link + "#" + name
            
            if country.upper() == "RU":
                ru_links.append((ping, new_link))
            else:
                not_ru_links.append((ping, new_link))
        
        time.sleep(DELAY)

    # Сортировка по пингу
    ru_links.sort(key=lambda x: x[0])
    not_ru_links.sort(key=lambda x: x[0])

    # Сохранение
    with open("subs/all_ru.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(link for _, link in ru_links))
    
    with open("subs/all_not_ru.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(link for _, link in not_ru_links))

    total = len(ru_links) + len(not_ru_links)
    print(f"\n🎉 Готово!")
    print(f"   🇷🇺 RU: {len(ru_links)}")
    print(f"   🌍 Не RU: {len(not_ru_links)}")
    print(f"   Всего: {total}")

    update_readme_stats(len(ru_links), len(not_ru_links), total)

if __name__ == "__main__":
    main()