# Блог rukazax

Статический блог на GitHub Pages: https://rukazax.github.io/

## Структура

```
index.html                     список статей
posts/<slug>.html              страницы статей (готовый HTML)
src/<slug>.md                  исходники статей в Markdown
assets/                        картинки и локальная копия mermaid
.nojekyll                      отключает сборку Jekyll — файлы отдаются как есть
```

## Как добавить статью

1. Положить исходник в `src/<slug>.md`.
2. Собрать HTML (тёмная вёрстка как у первой статьи) и положить в `posts/<slug>.html`.
3. Добавить карточку в `index.html`.
4. Закоммитить в `main` — Pages пересоберёт сайт автоматически (~30 секунд).
