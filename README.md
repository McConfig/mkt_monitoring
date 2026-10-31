## Описание

Этот проект представляет собой готовый стек для мониторинга устройств Mikrotik через API на основе Docker, который использует Grafana, Prometheus, [Blackbox Exporter](https://github.com/prometheus/blackbox_exporter) и [MKTXP Exporter](https://github.com/akpw/mktxp). Так же он включает в себя централизованную обработку журналов Mikrotik на основе предварительно настроенного стека [syslog-ng](https://www.syslog-ng.com/) / [Grafana Alloy](https://grafana.com/docs/alloy/latest/) / [Loki](https://grafana.com/docs/loki/latest). Для управления контейнерами в стек включён [Portainer](https://www.portainer.io/).

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

## Portainer

Portainer — веб-интерфейс для управления контейнерами, образами, томами и
сетями Docker. В стеке он не обязателен: всё то же самое делается командами
`docker compose`, но через браузер удобнее смотреть состояние контейнеров,
читатель логи и перезапускать сервисы.

Версия зафиксирована в `docker-compose.yml`:

```yaml
  portainer:
    image: portainer/portainer-ce:2.45.3
```

### Первый запуск и создание администратора

1. Проверить, что контейнер запущен:

```bash
docker ps --filter name=portainer --format '{{.Names}} {{.Status}} {{.Ports}}'
```

Ожидаемый результат — строка вида
`portainer Up 2 minutes 0.0.0.0:9000->9000/tcp, [::]:9000->9000/tcp`.

2. Получить одноразовый код настройки. Portainer 2.45 и новее при первом
   старте печатает его в лог и требует ввести на экране создания
   администратора:

```bash
docker logs portainer 2>&1 | grep -o 'setup_token=[a-f0-9]*' | tail -1
```

Ожидаемый вывод — строка вида
`setup_token=d4b297cdc3a9d8478d1887d579e35def5c15d7b4d1db38bb354a782b43318909`.
Код действует до создания первого администратора.

3. Открыть в браузере `http://10.0.0.9:9000`, вставить код на экране Setup,
   создать логин и пароль администратора. Пароль — не короче 12 символов.
   После создания администратора код становится недействительным, дальше
   вход идёт по логину и паролю.

4. Проверить, что API отвечает и показывает версию:

```bash
curl -s http://10.0.0.9:9000/api/system/status
```

Ожидаемый результат: `{"Version":"2.45.3","InstanceID":"..."}`.

### Где хранятся данные

Пользователи, настройки, сертификаты и подключения Portainer лежат в томе
`mkt_monitoring_portainer_data`, внутри контейнера это `/data`. На хосте том
находится по пути
`/var/lib/docker/volumes/mkt_monitoring_portainer_data/_data`.

Том входит в бэкап `pi-backups` (файл `portainer_data.tar` в релизе), поэтому
после переустановки системы администратора и настройки не нужно создавать
заново.

### Управление

Запустить или обновить после правки `docker-compose.yml`:

```bash
cd ~/lab/mkt_monitoring
docker compose up -d portainer
```

Остановить, не удаляя данные:

```bash
docker compose stop portainer
```

Посмотреть логи:

```bash
docker logs -f portainer
```

Полностью удалить контейнер и том с данными (необратимо):

```bash
docker compose rm -sf portainer
docker volume rm mkt_monitoring_portainer_data
```

Проверить доступность веб-интерфейса:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.9:9000
```

Ожидаемый результат: `200`.

### Безопасность

Portainer монтирует `/var/run/docker.sock`, то есть получает те же права, что
процесс Docker на хосте: через него можно запустить контейнер с доступом к
любым файлам системы. Поэтому:

- порт 9000 открыт только в локальной сети и не пробрасывается на роутере
  наружу;
- доступ к интерфейсу есть только у тех, кому доверено управление сервером;
- после смены пароля администратора старый пароль перестаёт действовать
  сразу, сессии других браузеров нужно завершить в разделе My account.

## Доступ снаружи по HTTPS

Grafana доступна из интернета по адресу `https://grafana.q1w2e3.ru`. Схема:

```
браузер → https://grafana.q1w2e3.ru:443 → роутер MikroTik (TLS-терминация)
        → http://10.0.0.9:3003 → Grafana
```

DNS-запись `grafana.q1w2e3.ru` указывает на внешний адрес роутера
`37.192.117.229`. Обратный прокси и сертификат Let's Encrypt настроены на
самом роутере (RouterOS 7.25, встроенные `/ip reverse-proxy` и ACME-клиент),
поэтому отдельный контейнер с nginx или Caddy не нужен.

Из локальной сети по имени `grafana.q1w2e3.ru` запрос идёт тем же путём:
адрес принадлежит роутеру, пакет попадает в цепочку `input`, а не в
`forward`, поэтому NAT-loopback не требуется. Прямой доступ
`http://10.0.0.9:3003` тоже работает и не закрывается.

### Что настроено на роутере

1. В цепочке `input` разрешены 80 и 443 с WAN — перед правилом
   `defconf: drop all not coming from LAN`.
2. Выпущен сертификат Let's Encrypt на `grafana.q1w2e3.ru` через ACME.
3. Служба `reverse-proxy` включена и слушает 443.
4. Создано правило прокси: SNI `grafana.q1w2e3.ru` → `10.0.0.9:3003`.

Команды для повторения на чистом роутере (RouterOS 7.25):

```bash
/ip firewall filter add chain=input action=accept protocol=tcp dst-port=80 \
  in-interface-list=WAN place-before=[find comment="defconf: drop all not coming from LAN"] \
  comment="ACME HTTP-01 Let's Encrypt"

/ip firewall filter add chain=input action=accept protocol=tcp dst-port=443 \
  in-interface-list=WAN place-before=[find comment="defconf: drop all not coming from LAN"] \
  comment="HTTPS reverse-proxy Grafana"

/certificate add-acme name=grafana.q1w2e3.ru \
  directory-url=https://acme-v02.api.letsencrypt.org/directory \
  domain-names=grafana.q1w2e3.ru

# дождаться выдачи, проверить статус
/certificate print detail where name~"grafana"

/ip service set reverse-proxy certificate=grafana.q1w2e3.ru disabled=no

/ip reverse-proxy add sni=grafana.q1w2e3.ru ip-address=10.0.0.9 port=3003 \
  certificate=grafana.q1w2e3.ru comment="Grafana on raspberry"
```

Служба `www` должна быть включена: встроенный ACME в RouterOS проверяет домен
методом HTTP-01, то есть Let's Encrypt обращается к
`http://grafana.q1w2e3.ru/.well-known/acme-challenge/...` на порт 80, и
отвечает на этот запрос именно служба `www`. Если её выключить, ACME
возвращает ошибку `connection refused`.

### Сертификат и продление

Сертификат выпускается на 90 дней и продлевается автоматически, когда
истекает 80% срока. Для продления порт 80 должен оставаться доступен из
интернета. Текущее состояние проверяется командой:

```bash
/certificate print detail where name~"grafana"
```

В поле `acme-status` будет либо `next update at 2027-01-11T03:29:29Z`, либо
текст ошибки. Правило прокси и служба ссылаются на сертификат по имени,
поэтому после продления ничего менять не нужно.

### Проверка

С сервера во внешней сети (в примере — VPS `185.42.163.200`):

```bash
openssl s_client -connect grafana.q1w2e3.ru:443 -servername grafana.q1w2e3.ru </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

Ожидаемый результат:

```
subject=CN=grafana.q1w2e3.ru
issuer=C=US, O=Let's Encrypt, CN=YR1
notBefore=Oct 31 03:29:30 2026 GMT
notAfter=Jan 29 03:29:29 2027 GMT
```

Проверка цепочки и ответа Grafana:

```bash
echo | openssl s_client -connect grafana.q1w2e3.ru:443 -servername grafana.q1w2e3.ru 2>/dev/null | grep "Verify return code"
curl -sI https://grafana.q1w2e3.ru | head -3
```

Ожидаемый результат: `Verify return code: 0 (ok)` и
`HTTP/1.1 302 Found` с `Location: /login`. В браузере открыть
`https://grafana.q1w2e3.ru`, войти под администратором.

### Настройки Grafana

В `docker-compose.yml` у сервиса `grafana` заданы:

```yaml
      GF_SERVER_ROOT_URL: https://grafana.q1w2e3.ru/
      GF_SERVER_DOMAIN: grafana.q1w2e3.ru
```

Они нужны, чтобы ссылки в письмах, редиректы после входа и ссылки
«поделиться» указывали на внешний HTTPS-адрес, а не на `localhost`.
После изменения этих переменных перезапустить только Grafana:

```bash
cd ~/lab/mkt_monitoring
docker compose up -d grafana
```

### Диагностика

- `acme-status` содержит `connection refused` — выключена служба `www` или нет
  правила файрвола для порта 80.
- `acme-status` содержит ошибку DNS — роутер не может разрешить имя, проверить
  `/ip dns print` и `:resolve grafana.q1w2e3.ru`.
- Сертификат есть, но браузер показывает ошибку — проверить, что в правиле
  `/ip reverse-proxy` указан `certificate=grafana.q1w2e3.ru`, а не `none`.
- Прокси отвечает, но Grafana не открывается — проверить
  `curl -I http://10.0.0.9:3003` и `docker logs grafana`.
- Логи самого прокси и ACME: `/log print where topics~"acme"` и
  `/log print where topics~"rproxy"`.

### Ограничения и безопасность

- Порт 80 занят службой `www`, поэтому `http://grafana.q1w2e3.ru` открывает
  страницу входа WebFig, а не перенаправляет на HTTPS. Порт 80 нужен для
  продления сертификата, поэтому просто выключить `www` нельзя.
- WebFig доступен из интернета по HTTP. Пароль администратора роутера должен
  быть длинным и уникальным, не таким, как пароли сервисов.
- Grafana доступна из интернета по паролю. Рекомендуется длинный уникальный
  пароль и включённая двухфакторная аутентификация в профиле пользователя.
- Встроенный прокси RouterOS работает по HTTP/1.1 и не поддерживает
  WebSocket, поэтому Grafana Live (живое обновление панелей) может не
  работать. Дашборды, графики и логи работают.

### Как отключить доступ снаружи

```bash
/ip reverse-proxy disable [find sni="grafana.q1w2e3.ru"]
/ip service disable reverse-proxy
/ip firewall filter remove [find comment~"ACME HTTP-01|HTTPS reverse-proxy"]
```

Службу `www` выключать только вместе с ACME-клиентом, иначе перестанет
продлеваться сертификат:

```bash
/certificate remove [find name~"grafana"]
/ip service disable www
```

## Логи роутеров

Все роутеры отправляют журналы на сервер мониторинга по syslog. Цепочка:
RouterOS → syslog-ng (`10.0.0.9:514/udp`) → Alloy (`:1514`) → Loki →
Grafana. Локально на роутерах остаются память и диск, поэтому журнал доступен
и без сервера.

Конфигурация приёма логов лежит в `alloy/config.alloy`. Компоненты:

- `loki.source.syslog.routers` — слушает TCP `0.0.0.0:1514`, разбирает
  RFC5424, сохраняет время из сообщения, помечает поток меткой `job="syslog"`;
- `loki.relabel.routers` — переносит служебные метки syslog в обычные
  (`routerboard`, `syslog_host`, `topic`, `topics`, `severity`) и заменяет
  уровень `informational` на `info`;
- `loki.process.routers` — отбрасывает служебные строки mktxp и маркер
  syslog-ng;
- `loki.write.default` — отправляет записи в `http://loki:3100/loki/api/v1/push`.

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

Alloy раскладывает сообщения по меткам:

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
`docker logs alloy`, затем запрос в Loki.

Отдельно проверяется, что Alloy принимает записи и отправляет их в Loki:

```bash
curl -s http://10.0.0.9:9080/metrics | grep -E 'loki_source_syslog_entries_total|loki_write_sent_entries_total|loki_process_dropped_lines_total'
```

Ожидаемый результат: растущие счётчики `loki_source_syslog_entries_total` и
`loki_write_sent_entries_total`, а `loki_process_dropped_lines_total` растёт
только на служебных строках mktxp и маркере syslog-ng.

Если после перезапуска Alloy логи перестали поступать, перезапустить
syslog-ng: `docker restart syslog-ng`. В конфиге syslog-ng выставлены
`keep-alive(yes)` и `time-reopen(10)`, обычно переподключение происходит
самостоятельно в течение десяти секунд.

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
