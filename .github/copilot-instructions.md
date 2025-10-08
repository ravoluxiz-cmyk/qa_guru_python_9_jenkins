## Краткие инструкции для AI-агента (репозиторий qa_guru_python_9_jenkins)

Цель: помочь агенту быстро понять проект, запуск тестов и характерные паттерны кода.

1) Большая картина
- Проект — набор автоматизированных тестов на Python + Selene/Selenium. Тесты находятся в `tests/`.
- Есть две логики: "simple" (мелкие/демо тесты) и "demoqa" (больше интеграционных UI тестов).
- Браузерная сессия создаётся через фикстуру `setup_browser` в `conftest.py` и возвращает объект Selene `Browser`.

2) Ключевые файлы и их роль
- `conftest.py` — центральная логика создания WebDriver: сначала пытается подключиться к Selenoid по `SELENOID_URL`, затем падает на локальный Chrome (webdriver-manager). Важные env-vars: `SELENOID_URL`, `BROWSER_VERSION`, `HEADLESS`.
- `requirements.txt` — зависимости. Обращай внимание на версию `selene==2.0.0b5`, которая фиксирует `webdriver-manager==3.7.0`.
- `pytest.ini` — добавлены опции для Allure: `--alluredir=allure-results`.
- `utils/attach.py` — функции для прикрепления артефактов (скриншот, логи, html, видео). Видео строится через базовый URL Selenoid: `https://selenoid.autotests.cloud/video/<session_id>.mp4`.
- `tests/demoqa/test_registration_form.py` — пример UI-теста: использует `setup_browser` и API Selene (например `browser.element(...).set_value(...)`).

3) Частые команды и рабочие потоки
- Установить зависимости: `python3 -m pip install -r requirements.txt`.
- Запуск всех тестов: `pytest` (опция Allure уже прописана в `pytest.ini`).
- Запуск конкретного теста: `pytest tests/demoqa/test_registration_form.py::test_successful -q`.
- Сгенерировать и просмотреть Allure отчет: `pytest` затем `allure serve allure-results` (если Allure установлен).

4) Важные нюансы и паттерны
- `setup_browser` может пропускать тест (pytest.skip), если нет ни Selenoid, ни локального chromedriver. Для локального драйвера проект использует `webdriver-manager` (автоматическая загрузка chromedriver).
- Если модифицируешь `conftest.py`, учитывай: разные версии Selenium/Selene могут иметь разный конструктор `Config`/`Browser`. В коде есть защитные блоки (try/except) — сохраняй их.
- При добавлении видео/логов используй `utils/attach.py`. Видео предполагает Selenoid; при локальном запуске URL будет недоступен — не ломай attach flow (они уже обёрнуты в try/except).
- Тесты в `tests/simple/test_fail.py` намеренно падают — не удаляй их без согласования.

5) Интеграции и ограничения
- Внешние сервисы: Selenoid (`selenoid.autotests.cloud`) для видео/VNC. Если Selenoid доступен, `SELENOID_URL` содержит учетные данные (в текущем коде встроен URL с логином). Лучше выносить креды в секреты/CI.
- Версии зависимостей важно держать совместимыми: `selene==2.0.0b5` ↔ `webdriver-manager==3.7.0`.

6) Конкретные рекомендации для AI-агента при изменениях
- При изменении браузерного запуска: поддержи оба варианта — remote (Selenoid) и local (webdriver-manager). Добавь явные env-vars в top of `conftest.py` и обнови README.
- При добавлении новых UI-тестов: используйте `setup_browser` fixture и Selene API (`browser.element(...).should(have.text(...))`). Пример: `tests/demoqa/test_registration_form.py`.
- При редактировании `utils/attach.py` — не удаляй существующие имена вложений (screenshot, browser_logs, page_source, video_+session).

7) Примеры паттернов (копировать для PR)
- Как открыть страницу и проверить текст:
  browser.open("https://demoqa.com/automation-practice-form")
  browser.element(".practice-form-wrapper").should(have.text("Student Registration Form"))

- Как прикрепить скриншот в teardown: `attach.add_screenshot(browser)` (см. `conftest.py`)

Если что-то в репозитории не однозначно — скажи, что непонятно (например: target CI runner, URL Selenoid/credentials, нужен ли headless всегда). Готов скорректировать инструкцию.
