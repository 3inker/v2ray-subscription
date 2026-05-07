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

country_flags = {
    "RU": "🇷🇺", "UA": "🇺🇦", "BY": "🇧🇾", "PL": "🇵🇱", "CZ": "🇨🇿", "SK": "🇸🇰",
    "DE": "🇩🇪", "FR": "🇫🇷", "GB": "🇬🇧", "IT": "🇮🇹", "ES": "🇪🇸", "NL": "🇳🇱",
    "BE": "🇧🇪", "AT": "🇦🇹", "CH": "🇨🇭", "SE": "🇸🇪", "NO": "🇳🇴", "FI": "🇫🇮",
    "DK": "🇩🇰", "IE": "🇮🇪", "PT": "🇵🇹", "GR": "🇬🇷", "HU": "🇭🇺", "RO": "🇷🇴",
    "BG": "🇧🇬", "RS": "🇷🇸", "HR": "🇭🇷", "LT": "🇱🇹", "LV": "🇱🇻", "EE": "🇪🇪",
    "MD": "🇲🇩", "AM": "🇦🇲", "GE": "🇬🇪", "AZ": "🇦🇿", "KZ": "🇰🇿", "LU": "🇱🇺",
    "US": "🇺🇸", "CA": "🇨🇦", "BR": "🇧🇷", "MX": "🇲🇽", "SG": "🇸🇬", "HK": "🇭🇰",
    "JP": "🇯🇵", "KR": "🇰🇷", "TW": "🇹🇼", "IN": "🇮🇳", "TR": "🇹🇷", "AE": "🇦🇪",
    "ID": "🇮🇩", "MY": "🇲🇾", "TH": "🇹🇭", "VN": "🇻🇳", "AU": "🇦🇺", "ZA": "🇿🇦",
}

def get_flag(country: str) -> str:
    if not country or country == "Unknown":
        return "🌍"
    country = country.upper()
    return country_flags.get(country, f"🌍 {country}")

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
    """Улучшенное извлечение адреса и порта"""
    try:
        # VMess
        if link.startswith("vmess://"):
            b64 = link[8:].split("?")[0].split("#")[0]
            data = json.loads(base64.b64decode(b64 + "==").decode(errors='ignore'))
            return data.get("add") or data.get("address"), int(data.get("port", 443))

        # VLESS, Trojan и другие
        if "://" in link:
            # Убираем параметры после ?
            clean_link = link.split("?")[0]
            parsed = urlparse(clean_link)
            addr = parsed.hostname
            port = parsed.port or 443

            # Если hostname пустой — пытаемся вытащить из пути
            if not addr and "@" in clean_link:
                addr_part = clean_link.split("@")[1].split(":")[0]
                addr = addr_part.split("/")[0]
            return addr, port
    except:
        pass
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

def get_country_and_provider(link):
    server, _ = get_server_address(link)
    if not server or not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", server):
        return "Unknown", "Unknown"
    
    try:
        r = requests.get(f"http://ip-api.com/json/{server}?fields=countryCode,org,isp", timeout=6)
        if r.status_code == 200:
            data = r.json()
            country = data.get("countryCode", "Unknown")
            provider = data.get("org") or data.get("isp") or "Unknown"
            
            for name in ["Cloudflare", "Hetzner", "Aeza", "Contabo", "OVH", "Amazon", "Google", "Oracle"]:
                if name.lower() in provider.lower():
                    provider = name
                    break
            else:
                provider = provider.split()[0][:25]
            return country, provider
    except:
        pass
    return "Unknown", "Unknown"

def update_readme_stats():
    subs_dir = Path("subs")
    if not subs_dir.exists():
        return

    # Статистика по протоколам
    proto_stats = {
        "all": len(open(subs_dir/"all.txt").readlines()) if (subs_dir/"all.txt").exists() else 0,
        "vless": len(open(subs_dir/"vless_all.txt").readlines()) if (subs_dir/"vless_all.txt").exists() else 0,
        "vmess": len(open(subs_dir/"vmess_all.txt").readlines()) if (subs_dir/"vmess_all.txt").exists() else 0,
        "trojan": len(open(subs_dir/"trojan_all.txt").readlines()) if (subs_dir/"trojan_all.txt").exists() else 0,
        "ss": len(open(subs_dir/"ss_all.txt").readlines()) if (subs_dir/"ss_all.txt").exists() else 0,
        "hy2": len(open(subs_dir/"hy2_all.txt").readlines()) if (subs_dir/"hy2_all.txt").exists() else 0,
    }

    # Статистика по странам (только VLESS)
    country_stats = {}
    for file in subs_dir.glob("vless_*.txt"):
        if file.name.endswith("_all.txt"):
            continue
        country = file.stem.replace("vless_", "")
        try:
            count = len(open(file, encoding="utf-8").readlines())
            country_stats[country] = count
        except:
            pass

    # Обновляем README
    readme_path = Path("README.md")
    if not readme_path.exists():
        return

    content = readme_path.read_text(encoding="utf-8")

    # Обновляем статистику протоколов
    content = re.sub(r"\*\*Все протоколы\*\*\s+\|\s+`\d+`", f"**Все протоколы**          | `{proto_stats['all']}`", content)
    content = re.sub(r"\*\*VLESS All\*\*\s+\|\s+`\d+`", f"**VLESS All**              | `{proto_stats['vless']}`", content)
    content = re.sub(r"\*\*VMess All\*\*\s+\|\s+`\d+`", f"**VMess All**              | `{proto_stats['vmess']}`", content)
    content = re.sub(r"\*\*Trojan All\*\*\s+\|\s+`\d+`", f"**Trojan All**             | `{proto_stats['trojan']}`", content)
    content = re.sub(r"\*\*Shadowsocks All\*\*\s+\|\s+`\d+`", f"**Shadowsocks All**        | `{proto_stats['ss']}`", content)
    content = re.sub(r"\*\*Hysteria2 All\*\*\s+\|\s+`\d+`", f"**Hysteria2 All**          | `{proto_stats['hy2']}`", content)

    # Таблица по странам
    country_table = "| Страна | Код | VLESS |\n|--------|-----|-------|\n"
    for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:20]:
        flag = get_flag(country)
        country_table += f"| {flag} {country} | `{country}` | `{count}` |\n"

    content = re.sub(
        r"(### 🌍 Топ стран \(VLESS\)\n\n)([\s\S]*?)(?=\n\n###|\n\n##)", 
        f"### 🌍 Топ стран (VLESS)\n\n{country_table}\n", 
        content
    )

    # Дата обновления
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
            print("   ✅ Добавлена своя ссылка")
        elif is_subscription_url(item):
            content = fetch_with_retry(item)
            if content:
                decoded = try_decode_base64(content)
                if decoded:
                    content = decoded
                valid = [l for l in clean_content(content) if is_proxy_link(l)]
                all_links.update(valid)
                print(f"   ✅ Найдено {len(valid)} ссылок")

    print(f"\n📊 Всего уникальных ссылок: {len(all_links)}")

    with open("subs/raw_all.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(all_links)))

    # Проверка
    print("🧪 Проверка серверов...")
    working = defaultdict(lambda: defaultdict(list))

    for i, link in enumerate(all_links):
        print(f"[{i+1}/{len(all_links)}] Проверка...", end="\r")
        ok, ping = tcp_test(link)
        if ok:
            proto = next((p for p in ["vless","vmess","trojan","ss","hy2"] if link.startswith(p+"://")), "other")
            country, provider = get_country_and_provider(link)
            working[proto][(country, provider)].append((ping, link))
        time.sleep(DELAY)

    # Сохранение
    for proto in ["vless", "vmess", "trojan", "ss", "hy2"]:
        if proto in working:
            all_links_proto = []
            for (country, provider), items in working[proto].items():
                items.sort(key=lambda x: x[0])
                for num, (ping, link) in enumerate(items, 1):
                    flag = get_flag(country)
                    name = f"{flag} {country} ({num}) | {provider} | 🫐"
                    new_link = link.rsplit("#", 1)[0] + "#" + name if "#" in link else link + "#" + name
                    all_links_proto.append(new_link)

            # Основные файлы
            with open(f"subs/{proto}_all.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(all_links_proto))
            with open(f"subs/{proto}.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(all_links_proto))

    # all.txt
    with open("subs/all.txt", "w", encoding="utf-8") as f:
        combined = []
        for p in ["vless", "vmess", "trojan", "ss", "hy2"]:
            if Path(f"subs/{p}_all.txt").exists():
                combined.extend(open(f"subs/{p}_all.txt", encoding="utf-8").readlines())
        f.write("".join(combined))

    print(f"\n🎉 Готово! Рабочих: {sum(len(v) for v in working.values())}")
    update_readme_stats()

if __name__ == "__main__":
    main()