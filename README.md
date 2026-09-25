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

## Начална снимка (hero)

Предпочитан размер за началната лента: **1920 × 1080 px** (16:9), JPEG или WebP, около 150–400 KB.

| | |
|---|---|
| Най-добре | 1920 × 1080 (16:9) |
| За кадъра на сегашната снимка (750:444 ≈ 1.69:1) | 1920 × 1140 |
| Минимум | 1600 × 900 |
| Сегашният `hero-george.jpg` | 750 × 444 — твърде малък за retina desktop |

Desktop hero-то е широка лента (`min-height` около 448–640 px, ширина на прозореца). Снимката се реже с `background-size: cover`. Дръжте лицето, раменете и микрофона в **долните две трети** — desktop качва кадъра на `center 64%`.

Слайдерът е в `index.html` под `header.slides`. Стрелки и точки се показват само при 2+ слайда; смяната е през 7 секунди (спира при hover/фокус и при `prefers-reduced-motion`).

```yaml
header:
  hide_title: true
  overlay_color: "#0b0620"
  overlay_filter: "linear-gradient(#0b0620b8, #0b0620c7)"
  slides:
    - image: /assets/images/hero-george.jpg
      alt: Георги Бакалов
    - image: /assets/images/hero-brand.jpg
      alt: Троен християнски алианс
      position: center center
      matte: false
```

Сложете файловете в `assets/images/`. `position` е по желание (`center 64%`, `center center` и т.н.). `matte: false` маха тъмното покритие — ползвайте го за вече тъмни бранд кадри.

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
| Заключени / абонаментски постове | Пропуснати; не се публикуват |
| Коментари (16 публични) | Премахнати, без заместител |
| Jetpack контактни форми (`/contact/`, `/contact-2/`, `/about/`) | Статична HTML форма към **Formspree** (`https://formspree.io/f/xzezvyob`, `formspree_endpoint` в `_config.yml`) |
| Търсене `?s=` | Lunr търсене на [`/search/`](/search/) |
| `/clients/` (Jetpack CRM) | Пренасочване към началото |
| `/mailinglist/` (MailChimp / Mautic) | Пренасочване към началото |
| `/register`, `/members`, `/activity`, `/groups`, `/chatroom`, `/activate` | Пренасочване към началото |
| Matomo, Mautic, Jetpack stats | Не се пренасят |
| Google Analytics | GA4 `G-9522BW7CV0` (`analytics` в `_config.yml`, само при `JEKYLL_ENV=production`) |
| Пагинация `/page/N/` | Запазена (10 поста на страница) |
| `/category/<slug>/` и `/tag/<slug>/` | `jekyll-archives` |
| YouTube embed-и и линкове за дарения | Остават статични |

## Какво трябва да направи собственикът

1. **Settings → Pages → Source: GitHub Actions.**
2. Formspree е вързан (`formspree_endpoint: https://formspree.io/f/xzezvyob`). Първото изпращане от нов домейн може да иска потвърждение в пощата на Formspree акаунта.
3. Когато сте готови за домейн: едната промяна на `baseurl`, файл `CNAME`, DNS (виж по-горе).

## Лиценз на съдържанието

Текстът и медията принадлежат на Апостолска Реформирана църква / Георги Бакалов. Темата Minimal Mistakes е MIT.
