---
title: "Блог"
permalink: "/blog/"
slug: "blog"
layout: "single"
author_profile: false
comments: false
wp_id: 18
---
{%- assign bg_months = "януари,февруари,март,април,май,юни,юли,август,септември,октомври,ноември,декември" | split: "," -%}
{%- assign blog_posts = site.posts | slice: 0, 20 -%}
<div class="entries-list blog-list">
{%- for post in blog_posts -%}
{%- if post.header.teaser -%}{%- assign teaser = post.header.teaser -%}{%- elsif post.image -%}{%- assign teaser = post.image -%}{%- else -%}{%- assign teaser = nil -%}{%- endif -%}
{%- assign title = post.title | markdownify | remove: "<p>" | remove: "</p>" | strip -%}
{%- assign month_index = post.date | date: "%-m" | minus: 1 -%}
<div class="list__item">
<article class="archive__item" itemscope itemtype="https://schema.org/CreativeWork">
{%- if teaser -%}
<div class="archive__item-teaser"><a href="{{ post.url | relative_url }}" tabindex="-1" aria-hidden="true"><img src="{{ teaser | relative_url }}" alt="" loading="lazy"></a></div>
{%- endif -%}
<div class="archive__item-body">
<h2 class="archive__item-title no_toc p-name" itemprop="headline"><a class="u-url" href="{{ post.url | relative_url }}" rel="permalink">{{ title }}</a></h2>
<p class="page__meta"><span class="page__meta-date"><i class="far fa-calendar-alt" aria-hidden="true"></i> <time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%-d" }} {{ bg_months[month_index] }} {{ post.date | date: "%Y" }} г.</time></span></p>
{%- if post.excerpt -%}
<p class="archive__item-excerpt p-summary" itemprop="description">{{ post.excerpt | markdownify | strip_html | truncate: 160 }}</p>
{%- endif -%}
</div>
</article>
</div>
{%- endfor -%}
</div>
<p class="archive__see-all"><a href="{{ '/year-archive/' | relative_url }}">Всички публикации →</a></p>
