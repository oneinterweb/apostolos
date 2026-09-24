# apostolos.bg: pre-migration survey (read-only)
Date: 2026-09-25 ~01:30 Dubai time. Nothing on WP, DNS, Cloudflare, or GitHub was changed.

## 1. Credential
- Vaultwarden (vault.allegiancemarketing.us, george@georgebakalov.net) is **LOCKED**. `unlock` failed with "No graphical password prompt available (zenity/kdialog required)", and `list` timed out. **The app password was NOT saved.** George has to unlock the vault (bw unlock), then create this item:
  - Name: "apostolos.bg WordPress application password"; username `theeditor167`; URI https://apostolos.bg/wp-admin
  - Note: "Burned: pasted in chat 2026-09-25. Revoke after the GitHub Pages migration."
- Because the vault was locked, the check for a prelomchurchbg or apostolos Cloudflare token item could not be done.
- The app password works for user **theeditor167** (it fails for `admin`). Its REST access is at least editor-level, and it can also read /wp/v2/plugins and /settings, so it is likely an administrator.

## 2. WordPress
- WordPress 7.1.2 (from the generator meta). Theme: **Affinity 1.0.8**, a classic theme with no child theme. Content is **Gutenberg blocks plus legacy classic HTML**. **There is no page builder** (no Elementor, Divi, or WPBakery).
- Site title: "Апостолска Реформирана църква". Tagline: "Ecclesia reformata semper reformanda". Timezone Europe/Sofia. Admin email: arnold@matt28hosting.com.
- Legacy hostnames in content: `new.apostolos.bg` (150 image refs in posts, now 301s to apex) and `georgebakalov.bg` (8). The staging host is zmxyr7ma98.wpdns.site.

### Plugins (active)
Akismet, All-in-One WP Migration + URL ext, Backuply, Fonts Plugin (olympus-google-fonts), GA Google Analytics, Jetpack 16.2 (contact forms, social menu, stats), Jetpack Boost, Jetpack CRM (zero-bs-crm, has a /clients/ portal), Jetpack Protect, Loginizer, Matomo, **Patreon WordPress 1.9.17**, WP Cerber, WP Mautic, Zapier.
Inactive: Hello Dolly, LeadConnector (+ troubleshooter), REST API Meta Support, SEObot, Site Kit.
**Not present:** WPML, Polylang, CF7, WPForms, WooCommerce, events, and donation plugins.

### Counts (X-WP-Total)
| type | publish | draft | private | other |
|---|---|---|---|---|
| posts | 370 | 19 | 0 | trash 1 |
| pages | 27 | 7 | 4 | |
| categories | 18 (17 in sitemap) | | | |
| tags | 193 (185 in sitemap) | | | |
| media | 344 (272 jpg, 68 png, 3 gif, 1 mp3) | | | |
| comments | 16 public / 17 all | | | |
| users | 3: admin, theeditor167, danielatrifonowa | | | |
Posts by year: 2014:23, 2015:20, 2016:19, 2017:13, 2018:13, 2020:2, **2021:161, 2022:73, 2023:41**, 2024:2, 2025:3.

### URLs / permalinks
- Permalinks are `/%postname%/` with **Cyrillic slugs** (percent-encoded). Taxonomy archives are at `/category/<slug>/` and `/tag/<slug>/`. Home shows the latest posts at 10 per page, so paginated archives exist (/page/N/).
- wp-sitemap.xml has 601 URLs: 370 posts, 28 pages, 17 categories, 185 tags, 1 post_format. The list is in `urls.txt`. It does **not** include /page/N/ pagination, feeds, or attachment pages.

### Language
Content is Bulgarian only. The WP locale is set to en_US (`<html lang="en-US">`, site language is empty). There is no multilingual plugin.

### Menus
- "New Main Menu" (location `top`): За АРЦ › Контакт | YouTube (bitly) | А/О (patreon.com/apostolos) | Абонамент (/mailinglist/) | Теми (category статии) › about 55 tag links | svoboda21.com | bulgariaforisrael.com | "apostolos.bg" → threefold.life
- Social menu (Jetpack): Подкаст (tun.in), Facebook, YouTube
- Unused menus: Footer Menu, Logged In Menu, Primary, Primary Menu

### Dynamic features to replace or drop on static hosting
- **Patreon gating: 183 of 370 posts are locked** ("To view this content, you must be a member…"). The full text is in the DB. The public HTML shows only a teaser and an unlock button.
- **Jetpack contact forms** on /contact/, /contact-2/, /about/ (sends to gpbakalov@gmail.com). Needs Formspree, Web3Forms, a CF Worker, or GHL.
- **Comments** are open on 365 posts, with only 16 approved. Freeze them as static text or drop them.
- **Search** (?s=). Needs Pagefind or Lunr.
- Mailing list page (legacy MailChimp embed and script). Mautic tracking.
- /clients/ Jetpack CRM portal with wp-login form. Old BuddyPress-style pages (/register, /members, /activity, /groups, /activate) and /chatroom/ with a chat embed. All likely dead.
- Donation pages (Philippines 2015/2016) use PayPal-style links and embeds. These are static links, so they are fine.
- About 36 posts with YouTube embeds and 17 with iframes. These work statically.
- Analytics: GA, Matomo (self-hosted inside WP, so it would be lost), Jetpack stats.

### Media
- Everything is hosted locally at apostolos.bg/wp-content/uploads (no Jetpack/Photon CDN in the REST data). **The 344 originals total about 89.5 MB** (HEAD content-length). Thumbnails add more, so expect about 150–250 MB for the full uploads directory. That is well under the 1 GB GitHub Pages limit.

## 3. DNS / hosting (public dig and DoH, cross-checked with 1.1.1.1 and 8.8.8.8)
- NS: daisy.ns.cloudflare.com, jose.ns.cloudflare.com. SOA serial 2414158074.
- apex A: 104.18.185.50 (Cloudflare proxied). No AAAA, **no MX, no TXT (no SPF), no _dmarc, no CAA**. Common DKIM selectors are also empty.
- www: CNAME to zmxyr7ma98.wpdns.site (proxied). www 301s to https://apostolos.bg/.
- new.apostolos.bg: 301 to apex.
- **Origin:** zmxyr7ma98.wpdns.site (104.17.144/145.110, wpdns.site sits on Cloudflare NS). The headers (s-maxage=2592000, cf-cache-status HIT, a WAF 403 page with an "RID" id) match a Cloudflare-fronted managed WP host. wpdns.site is used by **Rocket.net** (inferred, not confirmed). The admin email domain matt28hosting.com suggests a reseller or agency.
- **Email:** the apex has no mail records, so there is nothing email-related to preserve in the cutover. Direct queries to the Cloudflare authoritative NS timed out from the box (port 53 is blocked), but the DoH answers agree.
- Cloudflare zone: George confirmed it is in the **prelomchurchbg@gmail.com CF account**, not Allegiance. The Allegiance global-key lookup was skipped per instructions, so the zone id and full record list are **unknown** until someone has access to that account.
- WAF note: the origin WAF returns 403 for /wp-json/wp/v2/users/me with or without auth. Other authenticated REST calls work.

## 4. GitHub
- Both the GitHub-xai and cursor-github connectors authenticate as **oneinterweb** (id 125945910, "George B."). This is **not** confirmed to be the prelomchurchbg@gmail.com account. No orgs were listed (the public API was rate-limited).
- Public search found the user **prelombg** (id 333286353, a new account). It is a plausible candidate for the prelomchurchbg account, but that is unverified. Neither connector can act as it.

## Recommendation
See the final report. In short: **(a) static mirror first**, then optionally a later rebuild.

### Reasoning
- The site is a classic theme with plain block and HTML content and no builder. About 600 URLs and about 200 MB of media make a clean, fast crawl.
- **Patreon gating strongly favors (a).** A mirror captures the public teaser HTML only, so the paywall behavior is kept by default. A REST-based rebuild (b) pulls the raw content and would **publish 183 patron-only posts in full** unless the gated blocks are filtered out deliberately.
- (a) keeps the look and every Cyrillic URL exactly, with no redirect map needed. Mirror work: rewrite new.apostolos.bg image links to local paths, swap the Jetpack forms for Formspree or Web3Forms, drop comment forms, the search box, and the /clients/, /register/, /members/, /chatroom/ pages, and add Pagefind for search.
- (b) Astro or Hugo would give a cleaner long-term codebase, but it means redesigning the Affinity look, reimplementing the tag and category archives and pagination, and handling the paywall. It is a good phase 2 if the site will keep being edited. It is too much for a straight migration.
- GitHub Pages needs a custom domain CNAME file. Point the apex at the GitHub Pages IPs, or use CNAME flattening in the prelomchurchbg CF account, with the proxy off or on as appropriate. There are no mail records to worry about.
