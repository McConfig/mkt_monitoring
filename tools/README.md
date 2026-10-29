# Генераторы дашбордов Grafana

## Назначение

В каталоге лежат два Python-скрипта, которые собирают JSON-файлы дашбордов
для провижининга Grafana. JSON-файлы лежат в
`grafana/provisioning/dashboards/home/` и подхватываются Grafana автоматически.
Скрипты — источник правды: панели правятся в коде, а не в интерфейсе Grafana.

| Скрипт | Что собирает | Куда пишет |
|---|---|---|
| `gen_home_dash.py` | дашборд «Дом» (uid `dom`) | `grafana/provisioning/dashboards/home/home.json` |
| `gen_logs_dash.py` | дашборд «Логи» (uid `logs`) | `grafana/provisioning/dashboards/home/logs.json` |

Оба дашборда попадают в папку «Дом» (провайдер
`grafana/provisioning/dashboards/home.yml`).

## Требования

- Python 3.8 или новее.
- Сторонние библиотеки не нужны, используется только стандартная библиотека.
- Запускать можно на любом компьютере, где есть копия репозитория: скрипт сам
  определяет корень репозитория относительно своего расположения.

## Запуск

Из корня репозитория:

```bash
python3 tools/gen_home_dash.py
```

Ожидаемый вывод:

```
записано: /home/mcconfig/lab/mkt_monitoring/grafana/provisioning/dashboards/home/home.json
панелей: 55 id max: 55
```

Затем:

```bash
python3 tools/gen_logs_dash.py
```

Ожидаемый вывод:

```
записано: /home/mcconfig/lab/mkt_monitoring/grafana/provisioning/dashboards/home/logs.json
панелей: 15 id max: 15
```

## Как изменения попадают в Grafana

1. Провайдер провижининга настроен с `updateIntervalSeconds: 10`, поэтому
   изменённый JSON подхватывается в течение 10 секунд. Перезапуск Grafana не
   нужен.
2. Если добавляется новый файл провайдера (`*.yml`), тогда нужен перезапуск:

   ```bash
   cd ~/lab/mkt_monitoring
   docker compose restart grafana
   ```

3. Проверить, что дашборд загрузился:

   ```bash
   curl -s -u 'admin:ПАРОЛЬ' http://localhost:3003/api/dashboards/uid/dom \
     | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["dashboard"]["title"], len(d["dashboard"]["panels"]))'
   ```

   Для «Логов» замените `dom` на `logs`.

4. Открыть в браузере:

   - «Дом» — `http://10.0.0.9:3003/d/dom`
   - «Логи» — `http://10.0.0.9:3003/d/logs`

## Проверка перед коммитом

```bash
git diff --stat grafana/provisioning/dashboards/home/
git diff grafana/provisioning/dashboards/home/logs.json | head -40
```

Убедитесь, что в диффе только ожидаемые панели: генератор пересобирает файл
целиком, поэтому случайное изменение кода может переписать много строк.

Проверить, что все запросы валидны, можно через API Loki:

```bash
curl -s -G 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query=sum(count_over_time({job="syslog"}[5m]))'
```

## Откат

Если после генерации дашборд сломался:

```bash
git checkout -- grafana/provisioning/dashboards/home/home.json
```

или

```bash
git checkout -- grafana/provisioning/dashboards/home/logs.json
```

Grafana вернёт предыдущую версию в течение 10 секунд.

## Как устроены генераторы

- Датасурсы заданы константами в начале файла:
  - Prometheus: `PBFA97CFB590B2093`;
  - Loki: `P8E80F9AEF21F6940`.
- Сетка Grafana — 24 колонки. У каждой панели явно заданы `x`, `y`, `w`, `h`
  в `gridPos`. При добавлении панели в середину нужно сдвигать `y` у всех
  последующих панелей, иначе они наложатся друг на друга.
- `id` панелей генерируются автоматически счётчиком `nid()`.
- Заголовки, подписи и описания панелей — на русском языке.
- В «Доме» есть панели Loki (счётчики ошибок и предупреждений). Для них
  датасурс переопределяется на `LOKI` и в панели, и в запросе.

## Дашборд «Логи»

Разделы и панели:

1. «Обзор»
   - «Ошибки за 24 часа» — `severity=~"error|critical|emergency|alert"`;
   - «Предупреждения за 24 часа» — `severity="warning"`;
   - «Строк за 24 часа» — весь объём;
   - «Строк в минуту» — средний поток за 5 минут;
   - «Ошибки по роутерам» — разбивка по метке `routerboard`;
   - «Топ тем за 24 часа» — разбивка по метке `topic`.
2. «Динамика»
   - «Объём по уровням» — график по метке `severity`;
   - «Объём по роутерам» — график по метке `routerboard`.
3. «Ошибки и предупреждения»
   - «Сводка ошибок по роутерам и темам» — таблица;
   - «Последние ошибки и предупреждения» — живой список.
4. «Все логи»
   - «Живой поток с фильтрами» — переменные `routerboard`, `severity`,
     `topic` и произвольный текст `search`.

Переменные дашборда строятся по значениям меток Loki и обновляются
автоматически при появлении новых значений.

## Соглашения по меткам Loki

Promtail раскладывает сообщения RouterOS по меткам:

| Метка | Пример | Откуда берётся |
|---|---|---|
| `routerboard` | `gateway` | hostname в syslog-заголовке (имя роутера) |
| `topic` | `wireless` | первая тема из списка RouterOS |
| `topics` | `wireless,info` | полный список тем |
| `severity` | `error`, `informational` | важность из syslog-заголовка |

Служебные строки `user prometheus logged in/out` (переподключения mktxp) и
`-- MARK --` (маркер syslog-ng) отбрасываются на приёме.
