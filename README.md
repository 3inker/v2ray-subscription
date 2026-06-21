# 🚀 Free V2Ray Subscription

[![Last Commit](https://img.shields.io/github/last-commit/3inker/v2ray-subscription?style=for-the-badge)](https://github.com/3inker/v2ray-subscription/commits/main)
[![Workflow](https://img.shields.io/github/actions/workflow/status/3inker/v2ray-subscription/update.yml?style=for-the-badge)](https://github.com/3inker/v2ray-subscription/actions)
[![Stars](https://img.shields.io/github/stars/3inker/v2ray-subscription?style=for-the-badge)](https://github.com/3inker/v2ray-subscription/stargazers)

**Автоматический сборщик и проверщик бесплатных конфигов**

Поддерживаемые протоколы: **VLESS • VMess • Trojan • Shadowsocks • Hysteria2**

---

## 📊 Актуальная статистика

| Подписка | Количество | Ссылка |
| --- | --- | --- |
| **Все RU** | `52` | [all_ru.txt](https://raw.githubusercontent.com/3inker/v2ray-subscription/main/subs/all_ru.txt) |
| **Все не RU** | `509` | [all_not_ru.txt](https://raw.githubusercontent.com/3inker/v2ray-subscription/main/subs/all_not_ru.txt) |
| **Всего рабочих** | `561` | — |

---

## ✨ Как это работает

1. **Сбор** — скрипт загружает конфиги из источников в `sources.txt`. Поддерживаются как plain-text списки ссылок, так и **base64-подписки** (декодируются автоматически).
2. **Дедупликация** — удаляются профили с одинаковым сервером (`uuid + host + port`), даже если у них разные названия. Это то же самое, что кнопка «Удалить дубликаты» в VPN-клиентах.
3. **Проверка** — каждый уникальный сервер проверяется TCP-подключением. Нерабочие отбрасываются.
4. **Сортировка** — рабочие конфиги делятся на два файла по региону:
   - 🇷🇺 **all_ru.txt** — серверы с Россией в названии
   - 🌍 **all_not_ru.txt** — все остальные
5. **Обновление** — README автоматически обновляется со свежей статистикой и временем запуска.

---

## 📱 Как использовать

1. Выбери нужный файл из таблицы выше
2. Скопируй **raw-ссылку**
3. Вставь в клиент:

| Платформа | Клиенты |
| --- | --- |
| **Windows** | v2rayN, Hiddify, Happ |
| **Android** | V2rayNG, Exclave, Happ |
| **iOS** | Streisand, Happ, v2RayTun |

---

## ⚙️ Автоматизация

- Обновление каждые **12 часов** через GitHub Actions
- Дедупликация по `uuid + host + port` перед проверкой
- TCP-проверка работоспособности каждого сервера
- Автоматическое обновление статистики в этом README

---

*Последнее обновление: 2026-06-21 04:42 UTC*
