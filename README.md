# Гора Добра — Генератор постерів-патронажу

Локальний веб-застосунок для створення інфо-постерів дітей з діабетом для німецьких партнерів-патронів.

## Локальний запуск

```bash
pip install -r requirements.txt
python -m playwright install chromium chromium-headless-shell
python app/main.py
```

Відкрити http://localhost:5000

## Продакшн-деплой

Render.com:
1. Push репозиторій на GitHub
2. У Render: New → Web Service → підключити репо → deploy автоматично через `render.yaml`
3. Публічний URL: `https://<service-name>.onrender.com`

Контакти фонду редагуються у `config/fund.json` — зміна підтягнеться при наступному redeploy.
