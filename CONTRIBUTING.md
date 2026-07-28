# Участие в проекте

Спасибо за интерес к Marketing Analytics. Проект принимает улучшения
аналитики, импорта данных, PDF-отчётов, интерфейса и документации.

## Перед началом

1. Откройте Issue для новой функциональности или заметной правки.
2. Не добавляйте в репозиторий выгрузки клиентов, токены, логи и готовые PDF.
3. Для изменений зависимостей укажите причину и проверьте лицензию пакета.

## Локальная проверка

```powershell
python -m pip install -r backend\requirements.txt
cd frontend; npm.cmd ci; npm.cmd run build; cd ..
python -m py_compile backend\main.py backend\analytics.py backend\pdf_report.py
dotnet build desktop-webview2\SocialMetrics.Desktop.csproj -c Release
```

## Pull request

- Делайте один PR для одной понятной задачи.
- Опишите пользовательское влияние и способ проверки.
- Для интерфейса и PDF приложите скриншоты без клиентских данных.
- Не меняйте файлы в `dist/`, `build/`, `.next/`, `node_modules/` или локальные
  отчёты: они генерируются при сборке.

## Безопасность

Уязвимости, токены и персональные данные не публикуйте в Issue. Используйте
порядок из [SECURITY.md](SECURITY.md).
