---
title: "LLM Wiki — A Pattern for Building Personal Knowledge Bases"
type: source
date_ingested: 2026-04-11
source_type: note
url: local
tags: [knowledge-management, llm, personal-wiki, zettelkasten]
---

## Summary
Описывает паттерн для построения персональной базы знаний с помощью LLM-агента. Ключевая идея: вместо поиска по сырым документам в момент запроса (RAG), LLM инкрементально строит и поддерживает структурированную wiki — набор взаимосвязанных markdown-файлов. Знания компилируются один раз и обновляются при добавлении новых источников, а не переоткрываются каждый раз.

Система состоит из трёх слоёв: сырые источники (неизменяемые), wiki (принадлежит LLM), и схема (CLAUDE.md / AGENTS.md) — файл конфигурации, который делает LLM дисциплинированным редактором wiki, а не обычным чат-ботом.

Роли чётко разделены: пользователь — куратор и задаёт вопросы. LLM — исполняет всю рутину: суммаризацию, перекрёстные ссылки, архивирование, bookkeeping.

## Key Points
- Главное отличие от RAG: wiki — персистентный, накапливающийся артефакт. Кросс-ссылки уже построены, противоречия уже отмечены, синтез уже отражает всё прочитанное.
- Три операции: **Ingest** (добавление источника), **Query** (запрос к wiki), **Lint** (проверка здоровья wiki).
- `index.md` — навигационный каталог содержимого, читается при каждом запросе.
- `log.md` — append-only хронологический журнал всех операций.
- Результаты хороших запросов сохраняются обратно в wiki — знания накапливаются и от вопросов, не только от источников.
- Паттерн применим к: личному развитию, исследованиям, чтению книг, командным wiki, due diligence, хобби.
- Связан духовно с идеей Vannevar Bush «Memex» (1945) — личное хранилище знаний с ассоциативными связями.

## Entities Mentioned
- [[vannevar-bush]] — автор концепции Memex (1945), предшественник идеи

## Concepts Discussed
- [[rag-vs-wiki]] — сравнение подхода RAG и персистентной wiki
- [[knowledge-compounding]] — идея накопления знаний как центральная ценность паттерна
- [[wiki-maintenance]] — почему люди бросают wiki и почему LLM решает эту проблему

## Contradictions & Open Questions
- При большом масштабе (1000+ страниц) index.md как навигация перестаёт быть достаточным — нужен поиск (упоминается qmd).
- Обработка изображений в markdown остаётся неудобной — LLM не читает inline-изображения за один проход.

## Raw Excerpts
> "The wiki is a persistent, compounding artifact. The cross-references are already there. The contradictions have already been flagged."

> "LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass."

> "The human's job is to curate sources, direct the analysis, ask good questions, and think about what it all means. The LLM's job is everything else."
