## Описание

Этот проект представляет собой готовый стек для мониторинга устройств Mikrotik через API на основе Docker, который использует Grafana, Prometheus, [Blackbox Exporter](https://github.com/prometheus/blackbox_exporter) и [MKTXP Exporter](https://github.com/akpw/mktxp). Так же он включает в себя централизованную обработку журналов Mikrotik на основе предварительно настроенного стека [syslog-ng](https://www.syslog-ng.com/) / [promtail](https://grafana.com/docs/loki/latest/clients/promtail/) / [Loki](https://grafana.com/docs/loki/latest).

## Функции
- Мониторинг работы системы
  - утилизация диска
  - загрузка процессора
  - утилизация памяти
  - внешний IP-адрес (IPv4 и IPv6)
  - аптайм системы
  - температура
  - контроль напряжения
- Мониторинг интерфейса
  - трафик (bit/s)
  - трафик (packets/s)
  - пропускная способность канала
- Мониторинг latency
  - настраиваемые пинги ICMP и/или UDP
  - потеря пакетов
- DHCP-мониторинг
  - активная аренда
  - MAC-адреса, имена хостов, ip-адреса
- Мониторинг сети
  - маршруты
  - ошибки интерфейсов
  - состояния интерфейов
  - cостояние PoE
- BGP
  - Мониторинг сессии BGP (настраивается индивидуально)
- Мониторинг Firewall'а
  - rules traffic
  - logged rules traffic
  - Ipv4 & IPv6
  - активные пользователи
- Мониторинг беспроводных интерфейсов
  - noise floor - уровень шума
  - TxCCQ
  - устройства клиентов
  - количество клиентов
  - трафик
  - signal strength - сила сигнала
  - signal to noise ratio - отношение сигнал/шум
- Netwatch
- Мониторинг CAPsMAN
  - remote CAPS
  - registrations
  - clients
  - frequencies
  - signal strength
  - traffic
## Требования
- Роутер Mikrotik под управлением RouterOS 7.x.x
- Ubuntu Server 24.04 (протестировано мной)
## Демо изображения дашбордов

**Mikrotik MKTXP Monitoring**

![mktxp_1](./assets/mktxp_1.png)

<details><summary>Показать больше изображений</summary>
 
![mktxp_2](./assets/mktxp_2.png)
![mktxp_3](./assets/mktxp_3.png)
**Mikrotik Loki Logs**
![mkt_loki_logs](./assets/mkt_loki_logs.png)
**Grafana Internals**
![grafana](./assets/grafana.png)
**Prometheus 2.0 Stats**
![prometheus](./assets/prometheus.png)

</details>

## Установка и начало работы

### Подготовка Mikrotik

Первым делом нужно подготовить наш роутер.

Создаем группу которая будет иметь read-only доступ к API

```bash
/user group add name=prometheus policy=api,read
```

Создаем пользователя в этой группе:

```bash
/user add name=prometheus group=prometheus password=prometheus_user_password
```

Для для получения и обработки логов с нескольких устройств Mikrotik RouterOS в централизованном месте, нам нужно настроить наши устройства Mikrotik для отправки своих логов на указанный целевой сервер логов.

Настроим `logging action` (замените XX.XX.XX.XX на IP-адрес вашего сервера):

```bash
/system logging action
set remote bsd-syslog=yes name=remote remote=XX.XX.XX.XX remote-port=514 src-address=0.0.0.0 syslog-facility=local0 syslog-severity=auto target=remote
```
Далее изменяем соответствующие разделы логов для использования `logging action`:

```bash
/system logging
set 0 action=remote prefix=:Info
set 1 action=remote prefix=:Error
set 2 action=remote prefix=:Warning
set 3 action=remote prefix=:Critical

add action=remote disabled=no prefix=:Firewall topics=firewall
add action=remote disabled=no prefix=:Account topics=account
add action=remote disabled=no prefix=:Caps topics=caps
add action=remote disabled=no prefix=:Wireles topics=wireless
```

При необходимости вы можете расширить приведенный выше список, следуя [документации](https://help.mikrotik.com/docs/display/ROS/Log) RouterOS, предоставленной Mikrotik.

### Подготовка сервера

Устанавливаем Docker

```bash
bash <(curl -sSL https://get.docker.com)
```

Добавляем текущего пользователя в группу `docker`

```bash
sudo usermod -aG docker ${USER}
```

После выполнения команды выйдите из системы и войдите снова, чтобы изменения вступили в силу. Или используйте команду:

```bash
newgrp docker
```

Клонируем репозиторий и переходим в директорию `mkt_monitoring`:

```bash
git clone https://github.com/metgen/mkt_monitoring.git
cd mkt_monitoring
```

### Конфигурация экспортера MKTXP

Отредактируем основной файл конфигурации mktxp, добавив IP-адрес вашего устройства Mikrotik и информацию для аутентификации:

```bash
nano mktxp/mktxp.conf
```

>Вы можете добавить в мониторинг несколько устройств Mikrotik. Просто добавьте его в `mktxp/mktxp.conf`как предыдущее.

### Настраиваем мониторинг задержек

В этом проекте используется Blackbox Exporter для измерения задержек сети. По умолчанию имеет три цели:

- 1.1.1.1 (Cloudflare DNS)
- 8.8.8.8 (Google DNS)
- 77.88.8.8 (Yandex DNS)

Их можно изменить в файле конфигурации Prometheus:

```bash
nano prometheus/prometheus.yml
```

### Запускаем docker-compose

Теперь все должно быть готово и можно переходить к запкуску контейнеров:

```bash
docker-compose up -d
```
Как только контейнеры будут запущены, откройте в своем веб-браузере Grafana по адресу `http://server_ip:3003`

Логин и пароль по умолчанию `admin`:`admin`

## Логи роутеров

Все роутеры отправляют журналы на сервер мониторинга по syslog. Цепочка:
RouterOS → syslog-ng (`10.0.0.9:514/udp`) → promtail (`:1514`) → Loki →
Grafana. Локально на роутерах остаются память и диск, поэтому журнал доступен
и без сервера.

### Что настроено на роутерах

Единый набор правил логирования на всех устройствах:

| Темы | Действие | Куда |
|---|---|---|
| `info`, `error`, `warning`, `critical` | `remote` | Loki |
| `info` | `memory` | локальный журнал в памяти |
| `error`, `warning`, `critical` | `disk` | файл `log.0.txt` на флешке |

Правила по отдельным темам (`firewall`, `account`, `caps`, `wireless`) не
нужны: любое сообщение уже имеет одну из важностей `info`/`error`/`warning`/
`critical`, а тема передаётся в заголовке syslog. Дублирующие правила давали
по две записи на каждое событие.

Действие `remote` настраивается так:

```bash
/system logging action set [find name=remote] remote=10.0.0.9 remote-port=514 \
  remote-protocol=udp remote-log-format=syslog syslog-time-format=iso8601 \
  syslog-severity=auto syslog-facility=local0 add-topics-string=yes
```

- `remote-log-format=syslog` — RouterOS передаёт своё имя (`/system identity`).
  Без этого syslog-ng подставляет reverse-DNS и роутеры попадают в Loki как
  IP-адреса.
- `syslog-time-format=iso8601` — время с часовым поясом, без сдвига на
  разницу между роутером и сервером.
- `add-topics-string=yes` — в заголовок попадает список тем, например
  `wireless,info`.

Правила создаются командами:

```bash
/system logging add topics=info action=memory
/system logging add topics=error action=disk
/system logging add topics=warning action=disk
/system logging add topics=critical action=disk
```

Проверить, что всё применилось:

```bash
/system logging print
/system logging action print where name=remote
```

### Метки в Loki

Promtail раскладывает сообщения по меткам:

| Метка | Пример | Откуда берётся |
|---|---|---|
| `routerboard` | `gateway` | имя роутера из syslog |
| `topic` | `wireless` | первая тема сообщения |
| `topics` | `wireless,info` | полный список тем |
| `severity` | `error` | важность сообщения |

На приёме отбрасываются служебные строки: `user prometheus logged in/out`
(переподключения mktxp к API) и `-- MARK --` (маркер syslog-ng).

### Проверка

Отправить тестовое сообщение с роутера:

```bash
/log info "проверка логирования"
```

Через несколько секунд оно должно появиться в Grafana в дашборде «Логи»
(`/d/logs`) с метками `routerboard`, `topic` и `severity`.

Проверить напрямую в Loki:

```bash
curl -s -G 'http://10.0.0.9:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={job="syslog"} |= "проверка логирования"' \
  --data-urlencode 'limit=5'
```

Проверить, что все роутеры на связи:

```bash
curl -s -G 'http://10.0.0.9:3100/loki/api/v1/query' \
  --data-urlencode 'query=sum by (routerboard) (count_over_time({job="syslog"}[1h]))'
```

### Дашборды

- «Дом» (`/d/dom`) — общий обзор, внизу счётчики ошибок и предупреждений
  за сутки и ссылка на «Логи».
- «Логи» (`/d/logs`) — ошибки и предупреждения за сутки, объём по уровням и
  роутерам, топ тем, сводная таблица ошибок, живые потоки с фильтрами по
  роутеру, уровню, теме и тексту.

Если логи не приходят, проверять по порядку: `/system logging print` на
роутере, доступность `10.0.0.9:514/udp`, `docker logs syslog-ng`,
`docker logs promtail`, затем запрос в Loki.

## Генераторы дашбордов

JSON дашбордов «Дом» и «Логи» собираются Python-скриптами из каталога
`tools/`. Править JSON руками не нужно: изменения вносятся в скрипт, после
чего файл пересобирается.

```bash
python3 tools/gen_home_dash.py
python3 tools/gen_logs_dash.py
```

Grafana подхватывает изменённые файлы провижининга в течение 10 секунд.
Подробности, структура дашбордов и порядок отката — в
[`tools/README.md`](tools/README.md).

## Ресурсы

Проект собран на основе двух репозиториев:

- [akpw/mktxp-stack](https://github.com/akpw/mktxp-stack)
- [M0r13n/mikrotik_monitoring](https://github.com/M0r13n/mikrotik_monitoring)

## Почему используется API вместо SNMP для мониторинга?

Мониторинг на основе SNMP очень медленный. Обходы по SNMP медленны и нагружают процессор. API работает намного быстрее и меньше нагружает процессор отслеживаемого устройства.

Кроме того, API предлагает большую гибкость. Любую команду можно выполнить в RouterOS через API. Таким образом можно собирать сложные метрики.
