# Миграция от WordPress

Скриптовете тук пресъздават съдържанието на https://apostolos.bg от **публичния** REST API (`/wp-json/wp/v2/...`, без автентикация).

## Какво правят

| Скрипт | Роля |
|---|---|
| `migrate.py` | Сваля постове, страници, таксономии и медия; изключва Patreon-заключени постове; пише Markdown; сваля оригиналите на картинките; прави отчет |
| `verify_urls.py` | Сравнява `urls.txt` с `_site/` след `jekyll build` |

## Стартиране

```bash
python3 -m pip install -r migration/requirements.txt
python3 migration/migrate.py
python3 migration/verify_urls.py
```

Повторно сваляне на JSON (без да пипа вече свалени картинки):

```bash
python3 migration/migrate.py --refresh-api
```

Само конверсия от вече сваления JSON в `migration/raw/`:

```bash
python3 migration/migrate.py --from-cache
```

## Как се разпознава Patreon

Неавтентикираният REST API връща **това, което вижда публиката**: за заключен пост това е банерът `patreon-campaign-banner` / `Unlock with Patreon`, без пълния текст. Скриптът изключва тези постове изцяло (без тийзър). Списъкът е в `excluded-patreon.txt`.

Публичният HTML на сайта е зад Cloudflare challenge от този хост, затова детекцията е по REST markup, сверена с извадка (заключен пост ≈ само банер; свободен пост ≈ пълна статия без `patreon-unlock-post`).
