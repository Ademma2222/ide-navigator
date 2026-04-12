---
name: Git History Rewrite — Co-Authored-By removed
description: 2026-04-12 force push на master и dev/andrey — Диме нужно пересклонировать репо
type: project
---

## Что произошло (2026-04-12)

Андрей убрал строку `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` из всех коммитов через `git filter-branch`. История переписана, сделан `git push --force` на `master` и `dev/andrey`.

## Что делать Диме

**Вариант 1 (проще):** удалить локальный клон и склонировать заново:
```bash
rm -rf ide-navigator
git clone https://github.com/Ademma2222/ide-navigator
```

**Вариант 2:** сбросить локальные ветки на remote:
```bash
cd ide-navigator
git fetch origin
git checkout master && git reset --hard origin/master
git checkout dev/andrey && git reset --hard origin/dev/andrey
```

**Важно:** обычный `git pull` вызовет конфликты, потому что все хеши коммитов изменились.
