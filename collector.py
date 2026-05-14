import requests
import re
import time
import socket
import json
import base64
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

# ================= НАСТРОЙКИ =================
TIMEOUT = 10
DELAY = 0.12
MAX_RETRIES = 3
IP_CHECK_ATTEMPTS = 2
# ============================================

def dedup_key(link: str) -> str:
    """Ключ: proto + uuid + host + port (без query и #name) — как в vpn-клиентах"""
    try:
        if link.startswith("vmess://"):
            b64 = link[8:].split("?")[0].split("#")[0]
            data = json.loads(base64.b64decode(b64 + "==").decode(errors='ignore'))
            host = data.get("add") or data.get("address", "")
            port = str(data.get("port", ""))
            uid  = data.get("id", "")
            return f"vmess://{uid}@{host}:{port}"
        # vless://uuid@host:port?query#name → vless://uuid@host:port
        proto = link.split("://")[0]
        body  = link.split("://")[1].split("?")[0].split("#")[0]
        return f"{proto}://{body}"
    except:
        return link

def try_decode_base64(content: str) -> str:
    """Пробует декодировать base64, если контент на него похож"""
    stripped = content.strip()
    if "://" not in stripped and re.match(r'^[A-Za-z0-9+/=\s]+$', stripped):
        try:
            decoded = base64.b64decode(stripped + "==").decode("utf-8", errors="ignore")
            if "://" in decoded:
                return decoded
        except Exception:
            pass
    return content

def is_russian_server(name: str) -> bool:
    """Проверка по целым словам. Telegram-канал в конце имени не учитывается."""
    if not name:
        return False

    name = re.sub(r'TG:\s*@\S+', '', name, flags=re.IGNORECASE)
    text = unquote(name).upper()

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

def update_readme(ru_count: int, not_ru_count: int):
    """Обновляет статистику и дату в README.md"""
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("⚠️  README.md не найден, пропускаем обновление")
        return

    total = ru_count + not_ru_count
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = readme_path.read_text(encoding="utf-8")

    text = re.sub(
        r'(\|\s*\*\*Все RU\*\*\s*\|\s*)`\d+`',
        rf'\1`{ru_count}`',
        text
    )
    text = re.sub(
        r'(\|\s*\*\*Все не RU\*\*\s*\|\s*)`\d+`',
        rf'\1`{not_ru_count}`',
        text
    )
    text = re.sub(
        r'(\|\s*\*\*Всего рабочих\*\*\s*\|\s*)`\d+`',
        rf'\1`{total}`',
        text
    )

    text = re.sub(
        r'\*Последнее обновление:.*?\*',
        f'*Последнее обновление: {now}*',
        text
    )

    readme_path.write_text(text, encoding="utf-8")
    print(f"📝 README.md обновлён: RU={ru_count}, не RU={not_ru_count}, всего={total}, дата={now}")

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
                content = try_decode_base64(content)
                valid = [l for l in clean_content(content) if is_proxy_link(l)]
                all_links.update(valid)
                print(f"  ✅ {len(valid)} ссылок")

    # Дедупликация по uuid+host+port (как кнопка "удалить дубликаты" в vpn-клиенте)
    seen_keys = {}
    for link in all_links:
        key = dedup_key(link)
        if key not in seen_keys:
            seen_keys[key] = link
    unique_links = list(seen_keys.values())
    print(f"\n📊 Собрано: {len(all_links)} | После дедупликации: {len(unique_links)}")

    print("🧪 Проверка серверов...")

    ru_links = []
    not_ru_links = []

    for i, link in enumerate(unique_links):
        print(f"[{i+1}/{len(unique_links)}] Проверка...", end="\r")
        if tcp_test(link):
            name_part = unquote(link.split("#")[-1]) if "#" in link else ""
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

    update_readme(len(ru_links), len(not_ru_links))

if __name__ == "__main__":
    main()
