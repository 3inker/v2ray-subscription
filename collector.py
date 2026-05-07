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
DELAY = 0.12
MAX_RETRIES = 3
# ============================================

country_flags = {
    # Европа
    "RU": "🇷🇺", "UA": "🇺🇦", "BY": "🇧🇾", "PL": "🇵🇱", "CZ": "🇨🇿", "SK": "🇸🇰",
    "DE": "🇩🇪", "FR": "🇫🇷", "GB": "🇬🇧", "IT": "🇮🇹", "ES": "🇪🇸", "NL": "🇳🇱",
    "BE": "🇧🇪", "AT": "🇦🇹", "CH": "🇨🇭", "SE": "🇸🇪", "NO": "🇳🇴", "FI": "🇫🇮",
    "DK": "🇩🇰", "IE": "🇮🇪", "PT": "🇵🇹", "GR": "🇬🇷", "HU": "🇭🇺", "RO": "🇷🇴",
    "BG": "🇧🇬", "RS": "🇷🇸", "HR": "🇭🇷", "LT": "🇱🇹", "LV": "🇱🇻", "EE": "🇪🇪",
    "MD": "🇲🇩", "AM": "🇦🇲", "GE": "🇬🇪", "AZ": "🇦🇿", "KZ": "🇰🇿", "LU": "🇱🇺",
    "SI": "🇸🇮", "MK": "🇲🇰", "AL": "🇦🇱", "BA": "🇧🇦", "ME": "🇲🇪",
    # Америка и Азия
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
    try:
        if link.startswith("vmess://"):
            b64 = link[8:].split("?")[0].split("#")[0]
            data = json.loads(base64.b64decode(b64 + "==").decode(errors='ignore'))
            return data.get("add") or data.get("address"), int(data.get("port", 443))
        
        parsed = urlparse(link)
        addr = parsed.hostname
        port = parsed.port or 443
        if not addr and "@" in link:
            addr = link.split("@")[1].split(":")[0].split("/")[0]
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

def get_country_and_provider(link):
    server, _ = get_server_address(link)
    if not server or not re.match(r"^\d+\.\d+\.\d+\.\d+$", server):
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
    """Обновляет README.md со статистикой по протоколам и странам"""
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

    # Статистика по странам (для VLESS — самый популярный)
    country_stats = defaultdict(int)
    for file in subs_dir.glob("vless_*.txt"):
        if file.name == "vless_all.txt":
            continue
        country_code = file.name.replace("vless_", "").replace(".txt", "")
        count = len(open(file).readlines())
        country_stats[country_code] = count

    # Читаем README
    readme_path = Path("README.md")
    if not readme_path.exists():
        return

    content = readme_path.read_text(encoding="utf-8")

    # Обновляем общую статистику
    content = re.sub(r"\*\*Все протоколы\*\*\s+\|\s+`.*?`", f"**Все протоколы**          | `{proto_stats['all']}`", content)
    content = re.sub(r"\*\*VLESS All\*\*\s+\|\s+`.*?`", f"**VLESS All**              | `{proto_stats['vless']}`", content)
    content = re.sub(r"\*\*VMess All\*\*\s+\|\s+`.*?`", f"**VMess All**              | `{proto_stats['vmess']}`", content)
    content = re.sub(r"\*\*Trojan All\*\*\s+\|\s+`.*?`", f"**Trojan All**             | `{proto_stats['trojan']}`", content)
    content = re.sub(r"\*\*Shadowsocks All\*\*\s+\|\s+`.*?`", f"**Shadowsocks All**        | `{proto_stats['ss']}`", content)
    content = re.sub(r"\*\*Hysteria2 All\*\*\s+\|\s+`.*?`", f"**Hysteria2 All**          | `{proto_stats['hy2']}`", content)

    # === Таблица по странам ===
    country_table = "| Страна | Код | VLESS | \n|--------|-----|-------|\n"
    for country, count in sorted(country_stats.items(), key=lambda x: x[1], reverse=True)[:15]:  # топ-15
        flag = get_flag(country)
        country_table += f"| {flag} {country} | `{country}` | `{count}` |\n"

    # Заменяем секцию таблицы по странам
    if "Таблица по странам" in content:
        content = re.sub(r"(### Таблица по странам\n\n)(.*?)(?=\n\n###|\n\n##)", 
                        f"### Таблица по странам\n\n{country_table}\n", content, flags=re.DOTALL)
    else:
        # Добавляем новую секцию, если её нет
        insert = f"\n### 🌍 Топ стран (VLESS)\n\n{country_table}\n"
        content = content.replace("### Как использовать", insert + "### Как использовать")

    # Дата обновления
    content = re.sub(
        r"\*Последнее обновление: .*",
        f"*Последнее обновление: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        content
    )

    readme_path.write_text(content, encoding="utf-8")
    print("✅ README.md успешно обновлён (статистика + таблица по странам)")

def main():
    Path("subs").mkdir(exist_ok=True)

    print("\n🔄 Собираем источники...")
    all_links = set()

    sources = [line.strip() for line in Path("sources.txt").read_text(encoding="utf-8").splitlines() 
               if line.strip() and not line.startswith("#")]

    for item in sources:
        print(f"→ {item[:90]}{'...' if len(item) > 90 else ''}")
        
        if is_proxy_link(item):
            all_links.add(item)
            print("   ✅ Прямая ссылка")
        elif is_subscription_url(item):
            content = fetch_with_retry(item)
            if not content:
                print("   ❌ Не удалось скачать")
                continue
            decoded = try_decode_base64(content)
            if decoded:
                content = decoded
                print("   🔓 Base64 декодировано")
            valid = [l for l in clean_content(content) if is_proxy_link(l)]
            all_links.update(valid)
            print(f"   ✅ {len(valid)} ссылок")

    print(f"\n📊 Всего уникальных ссылок: {len(all_links)}")
    with open("subs/raw_all.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(all_links)))

    # Проверка
    print("\n🧪 Проверка TCP Connect...")
    working = defaultdict(lambda: defaultdict(list))

    for i, link in enumerate(all_links):
        print(f"[{i+1}/{len(all_links)}] Проверка...", end="\r")
        ok, ping = tcp_test(link)
        if ok:
            proto = next((p for p in ["vless","vmess","trojan","ss","hy2"] if link.startswith(p+"://")), "other")
            country, provider = get_country_and_provider(link)
            working[proto][(country, provider)].append((ping, link))
        time.sleep(DELAY)

    # Сохранение файлов
    total = 0
    proto_all = defaultdict(list)

    for proto in sorted(working):
        all_proto_links = []
        for (country, provider), items in working[proto].items():
            items.sort(key=lambda x: x[0])
            renamed = []
            for num, (ping, link) in enumerate(items, 1):
                flag = get_flag(country)
                name = f"{flag} {country} ({num}) | {provider} | 🫐"
                if "#" in link:
                    base = link.rsplit("#", 1)[0]
                    new_link = f"{base}#{name}"
                else:
                    new_link = f"{link}#{name}"
                renamed.append(new_link)
                all_proto_links.append(new_link)

            if renamed:
                with open(f"subs/{proto}_{country}.txt", "w", encoding="utf-8") as f:
                    f.write("\n".join(renamed))
                total += len(renamed)

        if all_proto_links:
            with open(f"subs/{proto}_all.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(all_proto_links))
            with open(f"subs/{proto}.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(all_proto_links))
            proto_all[proto] = all_proto_links

    # all.txt
    with open("subs/all.txt", "w", encoding="utf-8") as f:
        combined = []
        for p in ["vless", "vmess", "trojan", "ss", "hy2"]:
            combined.extend(proto_all.get(p, []))
        f.write("\n".join(combined))

    print(f"\n🎉 Готово! Рабочих найдено: {total}")

    # Обновляем README.md
    update_readme_stats()

if __name__ == "__main__":
    main()