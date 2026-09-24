# Апостолска Реформирана църква (apostolos.bg)

Статично Jekyll огледало на [apostolos.bg](https://apostolos.bg), тема [Minimal Mistakes](https://mademistakes.com/work/minimal-mistakes-jekyll-theme/), деплой към GitHub Pages чрез Actions.

Предварителен адрес: **https://oneinterweb.github.io/apostolos/** (`baseurl: "/apostolos"`).

## Локално пускане

Нужни са Ruby 3.2+, Bundler и (за повторна миграция) Python 3.

```bash
bundle install
bundle exec jekyll serve
```

Сайтът е на http://127.0.0.1:4000/apostolos/ .

Пълна повторна миграция от публичния WordPress REST API:

```bash
python3 -m pip install -r migration/requirements.txt
python3 migration/migrate.py
bundle exec jekyll build
python3 migration/verify_urls.py
```

Подробности: [`migration/README.md`](migration/README.md).

## Как да добавите публикация

1. Създайте файл в `_posts/` с име `ГГГГ-ММ-ДД-кратък-slug.md` (датата е в часова зона Europe/Sofia).
2. Попълнете YAML front matter. За да запазите точния WordPress адрес, задайте `permalink` със същия slug (включително кирилица):

```markdown
---
title: "Заглавие на публикацията"
date: 2026-09-24 12:00:00
permalink: /заглавие-на-публикацията/
slug: заглавие-на-публикацията
author: Георги Бакалов
categories:
  - статии
tags:
  - реформация
excerpt: "Кратко резюме за списъка и SEO."
header:
  teaser: /assets/uploads/2026/09/cover.jpg
---

Текстът е Markdown. HTML (например YouTube iframe) също е допустим.

![описание]({{ site.baseurl }}/assets/uploads/2026/09/snimka.jpg)
```

3. Сложете оригиналните картинки в `assets/uploads/ГГГГ/ММ/`, по същата схема като стария `wp-content/uploads`.
4. Commit и push към `main`. Actions прави build и публикува сайта.

Страниците живеят в `_pages/` със собствен `permalink: /slug/`.

## Превключване към домейн apostolos.bg

Промяната е нарочно едноредова, плюс DNS и един файл:

1. В `_config.yml` сменете **само** този ред:

   ```yaml
   baseurl: ""
   ```

   (сега е `baseurl: "/apostolos"`). По желание сменете и `url:` на `https://apostolos.bg`.

2. Добавете файл `CNAME` в корена на хранилището с един ред:

   ```
   apostolos.bg
   ```

   **Не** добавяйте `CNAME`, докато преглеждате сайта на `oneinterweb.github.io/apostolos/`.

3. В Cloudflare (акаунтът на prelomchurchbg) насочете apex `apostolos.bg` към GitHub Pages (A записи към [IP-тата на GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site) или CNAME flattening към `oneinterweb.github.io`). Препоръка за първото пускане: proxy **DNS only** (сива облачка), докато сертификатът се издаде.
4. В GitHub: **Settings → Pages → Source = GitHub Actions** (не „Deploy from a branch“). Custom domain: `apostolos.bg`.

Workflow-ът `.github/workflows/pages.yml` вече ползва `actions/configure-pages`, `actions/upload-pages-artifact` и `actions/deploy-pages`. След като домейнът е вързан, `base_path` от configure-pages става празен и съвпада с `baseurl: ""`.

## Премахнати / заменени функции

| WordPress | Тук |
|---|---|
| ~183 Patreon-заключени поста | Изцяло изключени (без тийзър). Списък: `migration/excluded-patreon.txt` |
| Коментари (16 публични) | Премахнати, без заместител |
| Jetpack контактни форми (`/contact/`, `/contact-2/`, `/about/`) | Статична HTML форма към **Formspree** (`formspree_endpoint` в `_config.yml`, placeholder) |
| Търсене `?s=` | Lunr търсене на [`/search/`](/search/) |
| `/clients/` (Jetpack CRM) | Пренасочване към началото |
| `/mailinglist/` (MailChimp / Mautic) | Пренасочване към началото |
| `/register`, `/members`, `/activity`, `/groups`, `/chatroom`, `/activate` | Пренасочване към началото |
| Matomo, Mautic, Jetpack stats | Не се пренасят |
| Google Analytics | Само закоментиран слот в `_config.yml` (в проучването няма запазен GA id) |
| Пагинация `/page/N/` | Запазена (10 поста на страница) |
| `/category/<slug>/` и `/tag/<slug>/` | `jekyll-archives` |
| YouTube embed-и и линкове за дарения | Остават статични |

## Какво трябва да направи собственикът

1. **Settings → Pages → Source: GitHub Actions.**
2. Създайте Formspree форма с доставка към `gpbakalov@gmail.com` и сменете `formspree_endpoint` в `_config.yml` (сега е `https://formspree.io/f/YOUR_FORM_ID`).
3. Когато сте готови за домейн: едната промяна на `baseurl`, файл `CNAME`, DNS (виж по-горе).
4. Patreon материалите остават само в WordPress / Patreon — този сайт нарочно не ги публикува.

## Лиценз на съдържанието

Текстът и медията принадлежат на Апостолска Реформирана църква / Георги Бакалов. Темата Minimal Mistakes е MIT.
