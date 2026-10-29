#!/usr/bin/env python3
"""Генератор дашборда «Дом» для Grafana (provisioning JSON)."""
import json
import os

DS = {"type": "prometheus", "uid": "PBFA97CFB590B2093"}
UID = "dom"
_id = [0]


def nid():
    _id[0] += 1
    return _id[0]


def tgt(expr, legend=None, instant=False, fmt=None, ref="A"):
    t = {"expr": expr, "refId": ref, "datasource": DS}
    if legend is not None:
        t["legendFormat"] = legend
    if instant:
        t["instant"] = True
        t["range"] = False
    if fmt:
        t["format"] = fmt
    return t


def base(panel_type, title, x, y, w, h, targets, unit=None, desc=None, extra_cfg=None,
         options=None, mappings=None, thresholds=None):
    p = {
        "id": nid(),
        "type": panel_type,
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": DS,
        "targets": targets,
        "fieldConfig": {
            "defaults": {"custom": {}, "color": {"mode": "palette-classic"}, "mappings": mappings or []},
            "overrides": [],
        },
        "options": options or {},
    }
    d = p["fieldConfig"]["defaults"]
    if unit:
        d["unit"] = unit
    if thresholds:
        d["thresholds"] = {"mode": "absolute", "steps": thresholds}
    if desc:
        p["description"] = desc
    if extra_cfg:
        d.update(extra_cfg)
    return p


def stat(title, x, y, w, h, expr, unit="short", mappings=None, thresholds=None, desc=None, decimals=1,
         legend=None):
    p = base("stat", title, x, y, w, h, [tgt(expr, legend)], unit=unit, mappings=mappings,
             thresholds=thresholds, desc=desc)
    p["fieldConfig"]["defaults"]["decimals"] = decimals
    p["options"] = {
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "auto",
        "textMode": "auto",
        "wideLayout": True,
    }
    return p


def ts(title, x, y, w, h, targets, unit="short", desc=None, fill=12, thresholds=None,
       stack=False, legend_opts=None):
    p = base("timeseries", title, x, y, w, h, targets, unit=unit, desc=desc, thresholds=thresholds)
    p["fieldConfig"]["defaults"]["custom"] = {
        "drawStyle": "line",
        "lineWidth": 1,
        "fillOpacity": fill,
        "gradientMode": "opacity",
        "showPoints": "never",
        "spanNulls": True,
        "axisPlacement": "auto",
        "axisLabel": "",
        "scaleDistribution": {"type": "linear"},
        "stacking": {"mode": "normal" if stack else "none", "group": "A"},
    }
    p["options"] = {
        "tooltip": {"mode": "multi", "sort": "desc"},
        "legend": legend_opts or {"displayMode": "list", "placement": "bottom", "showLegend": True,
                                  "calcs": ["lastNotNull", "max"]},
    }
    return p


def state(title, x, y, w, h, expr, desc=None, legend="{{instance}}"):
    p = base("state-timeline", title, x, y, w, h, [tgt(expr, legend)],
             mappings=[{"type": "value", "options": {
                 "0": {"text": "нет", "color": "red", "index": 0},
                 "1": {"text": "есть", "color": "green", "index": 1}}}],
             desc=desc)
    p["fieldConfig"]["defaults"]["color"] = {"mode": "thresholds"}
    p["options"] = {
        "mergeValues": True,
        "showValue": "auto",
        "alignValue": "center",
        "rowHeight": 0.85,
        "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
        "tooltip": {"mode": "single"},
    }
    return p


def table(title, x, y, w, h, targets, unit="short", desc=None, overrides=None,
          transformations=None, index=None):
    p = base("table", title, x, y, w, h, targets, unit=unit, desc=desc)
    p["fieldConfig"]["defaults"]["custom"] = {
        "align": "auto",
        "cellOptions": {"type": "auto"},
        "inspect": False,
    }
    if overrides:
        p["fieldConfig"]["overrides"] = overrides
    if transformations:
        p["transformations"] = transformations
        if index:
            transformations[2]["options"]["indexByName"] = index
    p["options"] = {
        "showHeader": True,
        "cellHeight": "sm",
        "footer": {"show": False, "reducer": ["sum"], "countRows": False, "fields": ""},
    }
    return p


def instant_table_opts(metric, hide, index=None):
    """Метки -> колонки, склейка кадров, скрытие служебных полей."""
    exclude = {"Time": True, metric: True, "Value": True, "__name__": True,
               "instance": True, "job": True, "routerboard_address": True,
               "routerboard_name": True}
    exclude.update(hide)
    return [
        {"id": "labelsToFields", "options": {"mode": "columns"}},
        {"id": "merge", "options": {}},
        {"id": "organize", "options": {"excludeByName": exclude, "renameByName": {}}},
    ]


def bargauge(title, x, y, w, h, expr, unit="short", desc=None, thresholds=None):
    p = base("bargauge", title, x, y, w, h, [tgt(expr, "{{interface}}")], unit=unit,
             desc=desc, thresholds=thresholds)
    p["fieldConfig"]["defaults"]["min"] = 0
    p["options"] = {
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "orientation": "horizontal",
        "displayMode": "gradient",
        "valueMode": "color",
        "namePlacement": "auto",
        "showUnfilled": True,
        "sizing": "auto",
        "minVizHeight": 16,
        "minVizWidth": 8,
    }
    return p


def row(title, y):
    _id[0] += 1
    return {"id": _id[0], "type": "row", "title": title, "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "panels": []}


panels = []
G = 'routerboard_name="gateway"'

# ---------- Обзор ----------
panels.append(row("Обзор", 0))
panels.append(stat("Интернет", 0, 1, 6, 4, 'probe_success{job="blackbox",instance="1.1.1.1"}',
                   mappings=[{"type": "value", "options": {
                       "0": {"text": "НЕТ", "color": "red", "index": 0},
                       "1": {"text": "ДА", "color": "green", "index": 1}}}],
                   desc="ICMP-проба до 1.1.1.1: отвечает ли интернет."))
panels.append(stat("Доступность сайтов", 6, 1, 6, 4,
                   'avg(probe_success{job="blackbox_https"}) * 100', unit="percent",
                   thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 70},
                               {"color": "green", "value": 95}],
                   desc="Доля HTTPS-проб, которые завершились успешно."))
panels.append(stat("BGP-сессия", 12, 1, 6, 4, "mktxp_bgp_established",
                   mappings=[{"type": "value", "options": {
                       "0": {"text": "НЕТ", "color": "red", "index": 0},
                       "1": {"text": "ДА", "color": "green", "index": 1}}}],
                   desc="Состояние BGP-сессии с antifilter.network."))
panels.append(stat("Туннель WireGuard", 18, 1, 6, 4, 'mktxp_netwatch_status{name="wg-watchdog"}',
                   mappings=[{"type": "value", "options": {
                       "0": {"text": "НЕТ", "color": "red", "index": 0},
                       "1": {"text": "ДА", "color": "green", "index": 1}}}],
                   desc="Netwatch-проверка доступности 10.75.66.1 через туннель."))

panels.append(stat("Задержка до 1.1.1.1", 0, 5, 6, 4,
                   'probe_icmp_duration_seconds{job="blackbox",instance="1.1.1.1",phase="rtt"} * 1000',
                   unit="ms", thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 60},
                                          {"color": "red", "value": 150}],
                   desc="Круговое время ICMP до 1.1.1.1."))
panels.append(stat("CPU роутера", 6, 5, 6, 4, f'mktxp_system_cpu_load{{{G}}}', unit="percent",
                   thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 60},
                               {"color": "red", "value": 85}],
                   desc="Загрузка CPU основного роутера."))
panels.append(stat("Температура роутера", 12, 5, 6, 4, f'mktxp_system_cpu_temperature{{{G}}}',
                   unit="celsius", decimals=0,
                   thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 65},
                               {"color": "red", "value": 75}],
                   desc="Температура CPU основного роутера."))
panels.append(stat("Роутер работает", 18, 5, 6, 4, f'mktxp_system_uptime{{{G}}}', unit="s",
                   desc="Аптайм основного роутера."))

# ---------- Интернет ----------
panels.append(row("Интернет", 9))
panels.append(ts("Скорость WAN", 0, 10, 12, 8, [
    tgt(f'rate(mktxp_interface_rx_byte_total{{{G},name="sfp1"}}[2m]) * 8', "входящая", ref="A"),
    tgt(f'rate(mktxp_interface_tx_byte_total{{{G},name="sfp1"}}[2m]) * 8', "исходящая", ref="B"),
], unit="bps", desc="Скорость на внешнем интерфейсе sfp1."))
panels.append(ts("Задержка ICMP", 12, 10, 12, 8,
                 [tgt('probe_icmp_duration_seconds{job="blackbox",phase="rtt"} * 1000', "{{instance}}")],
                 unit="ms", desc="Круговое время до 1.1.1.1, 8.8.8.8, 77.88.8.8."))
panels.append(state("Доступность сайтов", 0, 18, 24, 6,
                    'probe_success{job="blackbox_https"}',
                    desc="Зелёный — сайт открылся, красный — нет."))
panels.append(ts("Код ответа HTTPS", 0, 24, 24, 7,
                 [tgt('probe_http_status_code{job="blackbox_https"}', "{{instance}}")],
                 unit="short", desc="HTTP-код последнего ответа каждого сайта."))

# ---------- Туннель и BGP ----------
panels.append(row("Туннель и BGP", 31))
panels.append(ts("Трафик туннеля", 0, 32, 12, 8, [
    tgt(f'rate(mktxp_interface_rx_byte_total{{{G},name="to-hermes-server"}}[2m]) * 8', "из интернета", ref="A"),
    tgt(f'rate(mktxp_interface_tx_byte_total{{{G},name="to-hermes-server"}}[2m]) * 8', "в интернет", ref="B"),
], unit="bps", desc="Трафик через WireGuard-интерфейс to-hermes-server."))
panels.append(ts("BGP-префиксы", 12, 32, 12, 8,
                 [tgt("mktxp_bgp_prefix_count", "{{name}}")], unit="short",
                 desc="Сколько префиксов получено от antifilter.network."))
panels.append(stat("Uptime BGP-сессии", 0, 40, 8, 6, "mktxp_bgp_uptime / 1000",
                   unit="s", decimals=0, legend="{{name}}",
                   thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 300},
                               {"color": "green", "value": 3600}],
                   desc="Время с момента установления BGP-сессии. Красный — сессия поднялась меньше 5 минут назад, "
                        "оранжевый — меньше часа."))
panels.append(state("Состояние туннеля", 8, 40, 16, 6, f'mktxp_netwatch_status{{{G}}}',
                    desc="Netwatch-проверка 10.75.66.1 раз в 10 секунд.", legend="{{name}}"))

# ---------- Роутер ----------
panels.append(row("Роутер", 46))
panels.append(ts("CPU по роутерам", 0, 47, 12, 8,
                 [tgt("mktxp_system_cpu_load", "{{routerboard_name}}")], unit="percent",
                 desc="Загрузка CPU всех роутеров."))
panels.append(ts("Память по роутерам", 12, 47, 12, 8,
                 [tgt("(1 - mktxp_system_free_memory / mktxp_system_total_memory) * 100",
                      "{{routerboard_name}}")], unit="percent",
                 desc="Использование оперативной памяти."))
panels.append(ts("Температура по роутерам", 0, 55, 8, 6,
                 [tgt("mktxp_system_cpu_temperature", "{{routerboard_name}}")], unit="celsius",
                 desc="Температура CPU."))
panels.append(stat("Свободно на диске", 8, 55, 8, 6, f'mktxp_system_free_hdd_space{{{G}}}',
                   unit="bytes", decimals=0, desc="Свободное место на flash роутера."))
panels.append(ts("Соединения", 16, 55, 8, 6,
                 [tgt("mktxp_ip_connections_total", "{{routerboard_name}}")], unit="short",
                 desc="Количество записей в conntrack."))

# ---------- Wi-Fi и CAPsMAN ----------
panels.append(row("Wi-Fi и точки доступа", 61))
panels.append(stat("Точек на связи", 0, 62, 6, 4, "count(mktxp_capsman_remote_caps_info)",
                   unit="short", decimals=0,
                   thresholds=[{"color": "red", "value": None}, {"color": "orange", "value": 3},
                               {"color": "green", "value": 4}],
                   desc="Сколько CAP зарегистрировано на CAPsMAN. Всего в сети 4."))
panels.append(stat("Клиентов Wi-Fi", 6, 62, 6, 4, "sum(mktxp_capsman_registrations_count)",
                   unit="short", decimals=0, desc="Всего клиентов на всех радиоточках."))
panels.append(stat("Клиентов на 5 ГГц", 12, 62, 6, 4,
                   'sum(mktxp_capsman_registrations_count{interface=~".*-5g"})',
                   unit="short", decimals=0, desc="Клиенты на диапазоне 5 ГГц."))
panels.append(stat("Клиентов на 2.4 ГГц", 18, 62, 6, 4,
                   'sum(mktxp_capsman_registrations_count{interface=~".*-2g"})',
                   unit="short", decimals=0, desc="Клиенты на диапазоне 2.4 ГГц."))

panels.append(state("Точки на связи", 0, 66, 12, 6, "mktxp_capsman_remote_caps_info",
                    desc="Дорожка на каждую точку доступа. Пропуск данных означает, что точка отвалилась.",
                    legend="{{identity}}"))
panels.append(bargauge("Клиенты по радио", 12, 66, 12, 6,
                       "sum by (interface) (mktxp_capsman_registrations_count)",
                       desc="Сколько клиентов обслуживает каждое радио.",
                       thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 6},
                                   {"color": "red", "value": 10}]))

CAPS_JOIN = ('(mktxp_capsman_remote_caps_info * on(identity) group_left(newest_version)'
             ' label_replace(mktxp_system_update_available, "identity", "$1", "routerboard_name", "(.+)"))'
             ' or (label_replace(mktxp_capsman_remote_caps_info, "newest_version", "н/д", "", "")'
             ' unless on(identity) label_replace(mktxp_system_update_available, "identity", "$1",'
             ' "routerboard_name", "(.+)"))')

panels.append(table("Точки доступа", 0, 72, 8, 8, [
    tgt(CAPS_JOIN, "", instant=True, fmt="table", ref="A"),
], desc="CAP, зарегистрированные на CAPsMAN: текущая прошивка и доступная для обновления.",
   transformations=instant_table_opts("mktxp_capsman_remote_caps_info", {}),
   index={"identity": 0, "base_mac": 1, "version": 2, "newest_version": 3}))
panels.append(table("Клиенты Wi-Fi", 8, 72, 16, 8, [
    tgt("mktxp_capsman_clients_devices_info", "", instant=True, fmt="table", ref="A"),
], desc="Клиенты CAPsMAN: радио, SSID, сигнал, скорости, аптайм.",
   transformations=instant_table_opts("mktxp_capsman_clients_devices_info", {}),
   index={"dhcp_name": 0, "dhcp_address": 1, "interface": 2, "ssid": 3,
          "rx_signal": 4, "tx_rate": 5, "rx_rate": 6, "uptime": 7}))
panels.append(ts("Трафик клиентов (топ-5)", 0, 80, 24, 7,
                 [tgt('topk(5, sum by (dhcp_name) (rate(mktxp_capsman_clients_rx_bytes_total[5m])'
                      ' + rate(mktxp_capsman_clients_tx_bytes_total[5m])) * 8)',
                      "{{dhcp_name}}")], unit="bps",
                 desc="Пять самых активных клиентов Wi-Fi по суммарной скорости."))

# ---------- LAN ----------
panels.append(row("LAN", 87))
panels.append(ts("Трафик по портам", 0, 88, 16, 8,
                 [tgt(f'sum by (name) (rate(mktxp_interface_rx_byte_total{{{G},name=~"ether.*"}}[5m])'
                      f' + rate(mktxp_interface_tx_byte_total{{{G},name=~"ether.*"}}[5m])) * 8',
                      "{{name}}")], unit="bps",
                 desc="Суммарный трафик по Ethernet-портам роутера."))
panels.append(stat("DHCP-аренды", 16, 88, 8, 8,
                   'mktxp_dhcp_lease_active_count{routerboard_name="gateway",server="dhcp-lan"}',
                   unit="short", decimals=0, desc="Активные аренды DHCP в LAN."))

# ---------- Малина ----------
panels.append(row("Малина (10.0.0.9)", 96))
PI = 'instance="10.0.0.9:9100"'
panels.append(ts("CPU малины", 0, 97, 8, 6,
                 [tgt(f'100 - avg(rate(node_cpu_seconds_total{{{PI},mode="idle"}}[5m])) * 100', "CPU")],
                 unit="percent", desc="Загрузка CPU Raspberry Pi."))
panels.append(ts("Память малины", 8, 97, 8, 6,
                 [tgt(f'(1 - node_memory_MemAvailable_bytes{{{PI}}} / node_memory_MemTotal_bytes{{{PI}}}) * 100',
                      "память")], unit="percent", desc="Использование оперативной памяти."))
panels.append(stat("Диск малины", 16, 97, 4, 6,
                   f'(1 - node_filesystem_avail_bytes{{{PI},mountpoint="/"}}'
                   f' / node_filesystem_size_bytes{{{PI},mountpoint="/"}}) * 100',
                   unit="percent", decimals=0, desc="Занято места на корневом разделе."))
panels.append(stat("Температура малины", 20, 97, 4, 6,
                   f'node_hwmon_temp_celsius{{{PI},sensor="temp0"}}', unit="celsius", decimals=0,
                   desc="Температура SoC."))

# ---------- Сервер ----------
panels.append(row("Сервер туннеля (185.42.163.200)", 103))
SRV = 'instance="10.75.66.1:9100"'
panels.append(ts("CPU сервера", 0, 104, 8, 6,
                 [tgt(f'100 - avg(rate(node_cpu_seconds_total{{{SRV},mode="idle"}}[5m])) * 100', "CPU")],
                 unit="percent", desc="Загрузка CPU сервера."))
panels.append(ts("Память сервера", 8, 104, 8, 6,
                 [tgt(f'(1 - node_memory_MemAvailable_bytes{{{SRV}}} / node_memory_MemTotal_bytes{{{SRV}}}) * 100',
                      "память")], unit="percent", desc="Использование оперативной памяти."))
panels.append(stat("Диск сервера", 16, 104, 4, 6,
                   f'(1 - node_filesystem_avail_bytes{{{SRV},mountpoint="/"}}'
                   f' / node_filesystem_size_bytes{{{SRV},mountpoint="/"}}) * 100',
                   unit="percent", decimals=0, desc="Занято места на корневом разделе."))
panels.append(stat("Load average", 20, 104, 4, 6, f'node_load1{{{SRV}}}', unit="short", decimals=2,
                   desc="Средняя нагрузка за 1 минуту."))
panels.append(ts("Сеть сервера", 0, 110, 12, 7, [
    tgt(f'rate(node_network_receive_bytes_total{{{SRV},device="ens3"}}[5m]) * 8', "входящая", ref="A"),
    tgt(f'rate(node_network_transmit_bytes_total{{{SRV},device="ens3"}}[5m]) * 8', "исходящая", ref="B"),
], unit="bps", desc="Трафик на внешнем интерфейсе ens3."))
panels.append(stat("Сервер работает", 12, 110, 6, 7,
                   f'node_time_seconds{{{SRV}}} - node_boot_time_seconds{{{SRV}}}', unit="s",
                   desc="Аптайм сервера."))
panels.append(stat("Сервер доступен", 18, 110, 6, 7, f'up{{{SRV}}}',
                   mappings=[{"type": "value", "options": {
                       "0": {"text": "НЕТ", "color": "red", "index": 0},
                       "1": {"text": "ДА", "color": "green", "index": 1}}}],
                   desc="Опрос node_exporter сервера через туннель."))

# ---------- Логи ----------
LOKI = {"type": "loki", "uid": "P8E80F9AEF21F6940"}


def loki_stat(title, x, y, w, h, expr, thresholds=None, desc=None):
    p = stat(title, x, y, w, h, expr, thresholds=thresholds, desc=desc)
    p["datasource"] = LOKI
    t = p["targets"][0]
    t["datasource"] = LOKI
    t["queryType"] = "instant"
    t["instant"] = True
    t["range"] = False
    t["editorMode"] = "code"
    p["fieldConfig"]["defaults"]["noValue"] = "0"
    return p


def link_panel(title, x, y, w, h, content):
    p = base("text", title, x, y, w, h, [])
    p["options"] = {
        "mode": "markdown",
        "code": {"language": "plaintext", "showLineNumbers": False, "showMiniMap": False},
        "content": content,
    }
    return p


panels.append(row("Логи роутеров", 117))
panels.append(loki_stat("Ошибки за 24 часа", 0, 118, 6, 6,
                        'sum(count_over_time({job="syslog", '
                        'severity=~"error|critical|emergency|alert"}[24h]))',
                        thresholds=[{"color": "green", "value": None},
                                    {"color": "red", "value": 1}],
                        desc="Строки уровня error и выше со всех четырёх роутеров."))
panels.append(loki_stat("Предупреждения за 24 часа", 6, 118, 6, 6,
                        'sum(count_over_time({job="syslog", severity="warning"}[24h]))',
                        thresholds=[{"color": "green", "value": None},
                                    {"color": "orange", "value": 1}],
                        desc="Строки уровня warning со всех четырёх роутеров."))
panels.append(link_panel("Где смотреть логи", 12, 118, 12, 6,
                         "**Подробности:** живой поток, ошибки по роутерам и темам "
                         "— в дашборде [«Логи»](/d/logs).\n\n"
                         "Данные приходят по syslog на 10.0.0.9:514, хранятся в Loki."))

dashboard = {
    "uid": UID,
    "title": "Дом",
    "tags": ["дом", "сеть", "туннель"],
    "timezone": "browser",
    "editable": True,
    "graphTooltip": 1,
    "refresh": "30s",
    "time": {"from": "now-6h", "to": "now"},
    "timepicker": {},
    "schemaVersion": 39,
    "version": 1,
    "templating": {"list": []},
    "annotations": {"list": [{
        "builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
        "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts", "type": "dashboard"}]},
    "panels": panels,
}

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "grafana", "provisioning", "dashboards", "home", "home.json")
json.dump(dashboard, open(OUT, "w"), ensure_ascii=False, indent=2)
print("записано:", OUT)
print("панелей:", len(panels), "id max:", _id[0])
