#!/usr/bin/env python3
"""Генератор дашборда «Логи» для Grafana (provisioning JSON)."""
import json
import os

DS = {"type": "loki", "uid": "P8E80F9AEF21F6940"}
UID = "logs"
_id = [0]

SEL = '{job="syslog", routerboard=~"$routerboard"}'
SEL_ERR = '{job="syslog", routerboard=~"$routerboard", severity=~"error|critical|emergency|alert"}'
SEL_WARN = '{job="syslog", routerboard=~"$routerboard", severity="warning"}'
SEL_EW = '{job="syslog", routerboard=~"$routerboard", severity=~"error|critical|emergency|alert|warning"}'
SEL_TOPIC = '{job="syslog", routerboard=~"$routerboard", topic=~".+"}'
SEL_SEV = '{job="syslog", routerboard=~"$routerboard", severity=~".+"}'


def nid():
    _id[0] += 1
    return _id[0]


def tgt(expr, legend=None, instant=False, ref="A"):
    t = {"expr": expr, "refId": ref, "datasource": DS,
         "queryType": "instant" if instant else "range", "editorMode": "code"}
    if legend is not None:
        t["legendFormat"] = legend
    if instant:
        t["instant"] = True
        t["range"] = False
    return t


def base(panel_type, title, x, y, w, h, targets, desc=None, thresholds=None, unit=None):
    p = {
        "id": nid(),
        "type": panel_type,
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": DS,
        "targets": targets,
        "fieldConfig": {
            "defaults": {"custom": {}, "color": {"mode": "palette-classic"}, "mappings": []},
            "overrides": [],
        },
        "options": {},
    }
    d = p["fieldConfig"]["defaults"]
    if unit:
        d["unit"] = unit
    if thresholds:
        d["thresholds"] = {"mode": "absolute", "steps": thresholds}
    if desc:
        p["description"] = desc
    return p


def stat(title, x, y, w, h, expr, legend=None, desc=None, thresholds=None, decimals=0):
    p = base("stat", title, x, y, w, h, [tgt(expr, legend, instant=True)], desc=desc,
             thresholds=thresholds, unit="short")
    d = p["fieldConfig"]["defaults"]
    d["decimals"] = decimals
    d["noValue"] = "0"
    p["options"] = {
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "colorMode": "value",
        "graphMode": "none",
        "justifyMode": "auto",
        "textMode": "auto",
        "wideLayout": True,
    }
    return p


def ts(title, x, y, w, h, expr, legend, desc=None, stack=True):
    p = base("timeseries", title, x, y, w, h, [tgt(expr, legend)], desc=desc, unit="short")
    p["fieldConfig"]["defaults"]["custom"] = {
        "drawStyle": "bars",
        "lineWidth": 1,
        "fillOpacity": 60,
        "gradientMode": "none",
        "showPoints": "never",
        "barAlignment": 0,
        "spanNulls": True,
        "axisPlacement": "auto",
        "axisLabel": "",
        "scaleDistribution": {"type": "linear"},
        "stacking": {"mode": "normal" if stack else "none", "group": "A"},
    }
    p["options"] = {
        "tooltip": {"mode": "multi", "sort": "desc"},
        "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True,
                   "calcs": ["sum"]},
    }
    return p


def bargauge(title, x, y, w, h, expr, legend, desc=None):
    p = base("bargauge", title, x, y, w, h, [tgt(expr, legend, instant=True)], desc=desc,
             unit="short")
    d = p["fieldConfig"]["defaults"]
    d["min"] = 0
    d["noValue"] = "0"
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


def table(title, x, y, w, h, expr, desc=None):
    p = base("table", title, x, y, w, h, [tgt(expr, instant=True)], desc=desc, unit="short")
    p["fieldConfig"]["defaults"]["custom"] = {
        "align": "auto",
        "cellOptions": {"type": "auto"},
        "inspect": False,
    }
    p["transformations"] = [
        {"id": "labelsToFields", "options": {"mode": "columns"}},
        {"id": "merge", "options": {}},
        {"id": "organize", "options": {
            "excludeByName": {"Time": True},
            "renameByName": {"routerboard": "Роутер", "topic": "Тема", "Value": "Строк"},
        }},
    ]
    p["options"] = {
        "showHeader": True,
        "cellHeight": "sm",
        "footer": {"show": False, "reducer": ["sum"], "countRows": False, "fields": ""},
    }
    return p


def logs(title, x, y, w, h, expr, desc=None):
    p = base("logs", title, x, y, w, h, [tgt(expr)], desc=desc)
    p["options"] = {
        "showTime": True,
        "showLabels": False,
        "showCommonLabels": False,
        "wrapLines": True,
        "prettifyLogMessage": False,
        "enableLogDetails": True,
        "dedupStrategy": "none",
        "sortOrder": "Descending",
    }
    return p


def row(title, y):
    _id[0] += 1
    return {"id": _id[0], "type": "row", "title": title, "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "panels": []}


panels = []

# ---------- Обзор ----------
panels.append(row("Обзор", 0))
panels.append(stat("Ошибки за 24 часа", 0, 1, 6, 4,
                   f'sum(count_over_time({SEL_ERR}[24h]))',
                   desc="Строки уровня error и выше со всех выбранных роутеров за сутки.",
                   thresholds=[{"color": "green", "value": None}, {"color": "red", "value": 1}]))
panels.append(stat("Предупреждения за 24 часа", 6, 1, 6, 4,
                   f'sum(count_over_time({SEL_WARN}[24h]))',
                   desc="Строки уровня warning за сутки.",
                   thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 1}]))
panels.append(stat("Строк за 24 часа", 12, 1, 6, 4,
                   f'sum(count_over_time({SEL}[24h]))',
                   desc="Весь объём логов от роутеров за сутки."))
panels.append(stat("Строк в минуту", 18, 1, 6, 4,
                   f'sum(count_over_time({SEL}[5m])) / 5',
                   desc="Средний поток логов за последние 5 минут.", decimals=1))

panels.append(stat("Ошибки по роутерам", 0, 5, 12, 5,
                   f'sum by (routerboard) (count_over_time({SEL_ERR}[24h]))',
                   legend="{{routerboard}}",
                   desc="Количество ошибок и критических сообщений по каждому роутеру.",
                   thresholds=[{"color": "green", "value": None}, {"color": "red", "value": 1}]))
panels.append(bargauge("Топ тем за 24 часа", 12, 5, 12, 5,
                       f'topk(12, sum by (topic) (count_over_time({SEL_TOPIC}[24h])))',
                       legend="{{topic}}",
                       desc="Самые частые темы: wireless, dhcp, script, bgp, system и другие."))

# ---------- Динамика ----------
panels.append(row("Динамика", 10))
panels.append(ts("Объём по уровням", 0, 11, 12, 8,
                 f'sum by (severity) (count_over_time({SEL_SEV}[$__interval]))',
                 legend="{{severity}}",
                 desc="Сколько строк каждого уровня приходит в Loki."))
panels.append(ts("Объём по роутерам", 12, 11, 12, 8,
                 f'sum by (routerboard) (count_over_time({SEL}[$__interval]))',
                 legend="{{routerboard}}",
                 desc="Поток логов от каждого устройства."))

# ---------- Ошибки ----------
panels.append(row("Ошибки и предупреждения", 19))
panels.append(table("Сводка ошибок по роутерам и темам", 0, 20, 24, 7,
                    f'sum by (routerboard, topic) (count_over_time({SEL_ERR}[24h]))',
                    desc="Из чего складываются ошибки: роутер и тема сообщения."))
panels.append(logs("Последние ошибки и предупреждения", 0, 27, 24, 10, SEL_EW,
                   desc="Живой список сообщений уровня warning и выше со всех роутеров."))

# ---------- Все логи ----------
panels.append(row("Все логи", 37))
panels.append(logs("Живой поток с фильтрами", 0, 38, 24, 12,
                   '{job="syslog", routerboard=~"$routerboard", severity=~"$severity", '
                   'topic=~"$topic"} |~ "$search"',
                   desc="Фильтры сверху: роутер, уровень, тема и произвольный текст."))

dashboard = {
    "uid": UID,
    "title": "Логи",
    "tags": ["дом", "логи"],
    "timezone": "browser",
    "editable": True,
    "graphTooltip": 1,
    "refresh": "30s",
    "time": {"from": "now-24h", "to": "now"},
    "timepicker": {},
    "schemaVersion": 39,
    "version": 1,
    "templating": {"list": [
        {
            "name": "routerboard", "label": "Роутер", "type": "query", "datasource": DS,
            "includeAll": True, "allValue": ".*", "multi": True, "refresh": 1,
            "query": {"label": "routerboard", "type": 1, "stream": "", "values": [],
                      "refId": "LokiVariableQueryEditor-VariableQuery"},
            "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
            "options": [],
        },
        {
            "name": "severity", "label": "Уровень", "type": "query", "datasource": DS,
            "includeAll": True, "allValue": ".*", "multi": True, "refresh": 1,
            "query": {"label": "severity", "type": 1, "stream": "", "values": [],
                      "refId": "LokiVariableQueryEditor-VariableQuery"},
            "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
            "options": [],
        },
        {
            "name": "topic", "label": "Тема", "type": "query", "datasource": DS,
            "includeAll": True, "allValue": ".*", "multi": True, "refresh": 1,
            "query": {"label": "topic", "type": 1, "stream": "", "values": [],
                      "refId": "LokiVariableQueryEditor-VariableQuery"},
            "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
            "options": [],
        },
        {
            "name": "search", "label": "Поиск", "type": "textbox",
            "current": {"selected": False, "text": "", "value": ""},
            "options": [],
        },
    ]},
    "annotations": {"list": [{
        "builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
        "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts", "type": "dashboard"}]},
    "panels": panels,
}

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "grafana", "provisioning", "dashboards", "home", "logs.json")
json.dump(dashboard, open(OUT, "w"), ensure_ascii=False, indent=2)
print("записано:", OUT)
print("панелей:", len(panels), "id max:", _id[0])
