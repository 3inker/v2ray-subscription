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
| **Все RU** | `470` | [all_ru.txt](https://raw.githubusercontent.com/3inker/v2ray-subscription/main/subs/all_ru.txt) |
| **Все не RU** | `211` | [all_not_ru.txt](https://raw.githubusercontent.com/3inker/v2ray-subscription/main/subs/all_not_ru.txt) |
| **Всего рабочих** | `681` | — |

---

## ✨ Как это работает

1. **Сбор** — скрипт загружает конфиги из источников в `sources.txt`. Поддерживаются как plain-text списки ссылок, так и **base64-подписки** (декодируются автоматически).
2. **Проверка** — каждый сервер проверяется TCP-подключением. Нерабочие отбрасываются.
3. **Сортировка** — рабочие конфиги делятся на два файла по региону:
   - 🇷🇺 **all_ru.txt** — серверы с Россией в названии
   - 🌍 **all_not_ru.txt** — все остальные
4. **Обновление** — README автоматически обновляется со свежей статистикой и временем запуска.

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

- Обновление каждые **24 часа** через GitHub Actions
- TCP-проверка работоспособности каждого сервера
- Автоматическое обновление статистики в этом README

---

*Последнее обновление: 2026-05-10 03:38 UTC*