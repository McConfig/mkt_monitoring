#!/usr/bin/env bash
#
# add-site.sh — добавить новый сайт на обратный прокси RouterOS.
#
# Что делает скрипт:
#   1. проверяет аргументы, A-запись DNS и отсутствие дублей на роутере;
#   2. создаёт ACME-клиент RouterOS и ждёт, пока Let's Encrypt выпустит
#      сертификат на указанное имя (HTTP-01, нужен открытый порт 80);
#   3. создаёт правило /ip reverse-proxy: SNI <host> -> <ip>:<port>;
#   4. проверяет HTTPS и печатает итог.
#
# Использование:
#   ./tools/add-site.sh <host> <ip> <port> [комментарий]
#   ./tools/add-site.sh --dry-run <host> <ip> <port> [комментарий]
#
# Пример:
#   ./tools/add-site.sh home.q1w2e3.ru 10.0.0.9 8123 "Home Assistant"
#
# Переменные окружения:
#   ROUTER_HOST   адрес роутера (по умолчанию 10.0.0.1)
#   ROUTER_USER   пользователь SSH с правами full (по умолчанию mcconfig)
#   ACME_DIR      каталог ACME (по умолчанию Let's Encrypt)
#   DNS_RESOLVER  DNS-сервер для dig (по умолчанию 1.1.1.1)
#   FORCE         1 — продолжать, даже если A-запись не совпадает с WAN
#
# Требования:
#   - SSH-доступ к роутеру по ключу, без пароля;
#   - A-запись <host> указывает на внешний адрес роутера;
#   - порт 80 открыт с WAN, служба www включена, acme-plain=yes;
#   - на роутере настроены /ip reverse-proxy и правила файрвола 80/443.
#
# Удаление сайта:
#   ssh <ROUTER_USER>@<ROUTER_HOST> \
#     '/ip reverse-proxy remove [find sni="<host>"]; /certificate remove [find name="<host>"]'
#
set -euo pipefail

ROUTER_HOST=${ROUTER_HOST:-10.0.0.1}
ROUTER_USER=${ROUTER_USER:-mcconfig}
ACME_DIR=${ACME_DIR:-https://acme-v02.api.letsencrypt.org/directory}
DNS_RESOLVER=${DNS_RESOLVER:-1.1.1.1}
FORCE=${FORCE:-0}

usage() {
  cat <<'EOF'
Использование: ./tools/add-site.sh [--dry-run] <host> <ip> <port> [комментарий]

  host        DNS-имя, на которое выпускается сертификат (например, home.q1w2e3.ru)
  ip          адрес бэкенда в локальной сети (например, 10.0.0.9)
  port        порт бэкенда (например, 8123)
  комментарий подпись правила на роутере, по умолчанию равно host

  --dry-run   только показать команды, ничего не менять

Переменные окружения: ROUTER_HOST, ROUTER_USER, ACME_DIR, DNS_RESOLVER, FORCE.
EOF
}

die() {
  printf 'ошибка: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

run_remote() {
  if [ "$DRY_RUN" = "1" ]; then
    printf '>> ssh %s@%s %q\n' "$ROUTER_USER" "$ROUTER_HOST" "$1"
    return 0
  fi
  ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
    "$ROUTER_USER@$ROUTER_HOST" "$1"
}

resolve_a() {
  local name=$1 ip=""
  if command -v dig >/dev/null 2>&1; then
    ip=$(dig +short A "$name" @"$DNS_RESOLVER" 2>/dev/null | tail -1 || true)
  elif command -v host >/dev/null 2>&1; then
    ip=$(host -t A "$name" "$DNS_RESOLVER" 2>/dev/null | awk '/has address/ {print $NF}' | tail -1 || true)
  else
    ip=$(curl -s --max-time 8 "https://dns.google/resolve?name=$name&type=A" 2>/dev/null \
      | grep -o '"data":"[0-9.]*"' | head -1 | cut -d'"' -f4 || true)
  fi
  printf '%s' "$ip"
}

detect_wan() {
  run_remote '/ip address print terse' 2>/dev/null \
    | grep -o 'address=[0-9.]*' | cut -d= -f2 \
    | grep -Ev '^(10\.|127\.|169\.254\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)' \
    | head -1 || true
}

cert_status() {
  local detail
  detail=$(run_remote "/certificate print detail where name=\"$HOST\"" || true)
  printf '%s' "$detail" | tr '\n' ' ' | grep -o 'acme-status="[^"]*"' | head -1 \
    | sed 's/^acme-status="//; s/"$//' || true
}

DRY_RUN=0
case "${1:-}" in
  --dry-run) DRY_RUN=1; shift ;;
  -h|--help) usage; exit 0 ;;
esac

if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
  usage >&2
  exit 2
fi

HOST=$(printf '%s' "$1" | tr 'A-Z' 'a-z')
BACKEND_IP=$2
BACKEND_PORT=$3
COMMENT=${4:-$HOST}

if ! [[ $HOST =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$ ]]; then
  die "некорректное имя хоста: $HOST"
fi

if ! [[ $BACKEND_IP =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  die "некорректный адрес бэкенда: $BACKEND_IP"
fi
IFS=. read -r oct1 oct2 oct3 oct4 <<< "$BACKEND_IP"
for oct in "$oct1" "$oct2" "$oct3" "$oct4"; do
  [ "$((10#$oct))" -ge 0 ] && [ "$((10#$oct))" -le 255 ] || die "некорректный адрес бэкенда: $BACKEND_IP"
done

if ! [[ $BACKEND_PORT =~ ^[0-9]+$ ]]; then
  die "некорректный порт: $BACKEND_PORT"
fi
if [ "$((10#$BACKEND_PORT))" -lt 1 ] || [ "$((10#$BACKEND_PORT))" -gt 65535 ]; then
  die "порт должен быть от 1 до 65535: $BACKEND_PORT"
fi

if [ "$DRY_RUN" = "0" ]; then
  info "роутер: $ROUTER_USER@$ROUTER_HOST"
  ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
    "$ROUTER_USER@$ROUTER_HOST" '/system identity print' >/dev/null 2>&1 \
    || die "нет SSH-доступа к роутеру $ROUTER_USER@$ROUTER_HOST (нужен ключ, без пароля)"

  existing_rule=$(run_remote "/ip reverse-proxy print terse where sni=\"$HOST\"" 2>/dev/null | tr -d '\r' | sed '/^[[:space:]]*$/d' || true)
  if [ -n "$existing_rule" ]; then
    die "правило для $HOST уже существует: $existing_rule"
  fi

  existing_cert=$(run_remote "/certificate print detail where name=\"$HOST\"" 2>/dev/null | tr -d '\r' | sed '/^[[:space:]]*$/d' || true)
  if [ -n "$existing_cert" ]; then
    die "сертификат с именем $HOST уже существует (acme-status: $(cert_status)). Удалить: /certificate remove [find name=\"$HOST\"]"
  fi

  dns_ip=$(resolve_a "$HOST")
  [ -n "$dns_ip" ] || die "A-запись для $HOST не найдена (проверено через $DNS_RESOLVER)"
  info "DNS: $HOST -> $dns_ip"

  wan_ip=$(detect_wan)
  if [ -n "$wan_ip" ] && [ "$dns_ip" != "$wan_ip" ]; then
    if [ "$FORCE" = "1" ]; then
      info "предупреждение: DNS указывает на $dns_ip, внешний адрес роутера — $wan_ip; продолжаю из-за FORCE=1"
    else
      die "DNS указывает на $dns_ip, а внешний адрес роутера — $wan_ip. HTTP-01 не пройдёт. Исправьте A-запись или запустите с FORCE=1"
    fi
  fi

  firewall_rule=$(run_remote '/ip firewall filter print terse where comment~"ACME HTTP-01"' 2>/dev/null | tr -d '\r' | sed '/^[[:space:]]*$/d' || true)
  if [ -z "$firewall_rule" ]; then
    info "предупреждение: не найдено правило файрвола с комментарием \"ACME HTTP-01\""
  fi
fi

info "создаю ACME-клиент для $HOST"
run_remote "/certificate add-acme name=$HOST directory-url=$ACME_DIR domain-names=$HOST"

if [ "$DRY_RUN" = "1" ]; then
  info "создаю правило reverse-proxy"
  run_remote "/ip reverse-proxy add sni=$HOST ip-address=$BACKEND_IP port=$BACKEND_PORT certificate=$HOST comment=\"$COMMENT\""
  info "режим --dry-run: команды только показаны, роутер не менялся"
  exit 0
fi

info "жду выпуск сертификата, обычно 30-60 секунд (максимум 180)"
status=""
for _ in $(seq 1 36); do
  sleep 5
  status=$(cert_status)
  case "$status" in
    "next update at "*) break ;;
    *failed*|*error*|*Error*|*timeout*|*Timeout*) break ;;
  esac
done

case "$status" in
  "next update at "*)
    info "сертификат выпущен: $status"
    ;;
  *)
    run_remote "/certificate remove [find name=\"$HOST\"]" || true
    die "сертификат не выпущен: ${status:-нет статуса за 180 секунд}. ACME-запись удалена. Проверьте A-запись, порт 80 и службу www, затем повторите запуск"
    ;;
esac

info "создаю правило reverse-proxy"
run_remote "/ip reverse-proxy add sni=$HOST ip-address=$BACKEND_IP port=$BACKEND_PORT certificate=$HOST comment=\"$COMMENT\""

sleep 3
info ""
info "готово: https://$HOST -> http://$BACKEND_IP:$BACKEND_PORT"

if command -v openssl >/dev/null 2>&1; then
  cert_info=$(echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null \
    | openssl x509 -noout -subject -enddate 2>/dev/null || true)
  if [ -n "$cert_info" ]; then
    info "сертификат, который отдаёт роутер:"
    printf '%s\n' "$cert_info"
  else
    info "предупреждение: не удалось получить сертификат с $HOST:443, проверьте правило вручную"
  fi
fi

if command -v curl >/dev/null 2>&1; then
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$HOST/" || true)
  info "ответ https://$HOST/: ${code:-нет ответа}"
fi

info ""
info "проверить на роутере:"
info "  /ip reverse-proxy print terse where sni=\"$HOST\""
info "  /certificate print detail where name=\"$HOST\""
