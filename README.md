# Блог и сайт услуг rukazax

Сайт: https://rukazax.github.io/ · статика на GitHub Pages, без сборки на стороне GitHub (`.nojekyll`).

## Структура

```
index.html              лендинг услуг: тёмная/светлая тема, меню, форма заявки
posts/<slug>.html       страницы статей
src/<slug>.md           исходники статей в Markdown
assets/site.css         общие стили (темы через data-theme)
assets/app.js           тема, «бургер» при прокрутке, модальная форма
assets/covers/          обложки статей (они же og:image)
assets/...              скриншоты продуктов и локальная копия mermaid
.nojekyll               отключает сборку Jekyll
```

## Сборка

```bash
python build_blog.py   # posts/*.html + index.html + assets/site.css + assets/app.js
node ../tools/publish_site.mjs   # публикация в GitHub Pages через API
```

## Форма заявки

Отправка идёт напрямую с страницы на `rukazax@gmail.com` через FormSubmit
(`https://formsubmit.co/ajax/rukazax@gmail.com`), почтовый клиент не открывается.
При первой отправке сервис присылает на этот адрес письмо с ссылкой активации формы.

## Новая статья

1. `src/<slug>.md` — текст в Markdown.
2. Добавить запись в `POSTS` внутри `build_blog.py` (title, desc, tags, cover).
3. Положить обложку в `assets/covers/<slug>.png`.
4. `python build_blog.py` и опубликовать.
