#!/usr/bin/env bash
# Install Universal (if needed), start serve --demo, create sample agents.
# Safe to re-run. Does not kill an already-healthy factory.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PORT="${UNIVERSAL_DEMO_PORT:-43124}"
HOST="127.0.0.1"
BASE="http://${HOST}:${PORT}"
SKIP_INSTALL=0

usage() {
  cat <<EOF
Usage: ./demo.sh [--port PORT] [--skip-install]

  Installs the package (pip, editable), starts
  python3 -m universal serve --demo on 127.0.0.1:43124
  if /health is down, creates demo-researcher and demo-hook,
  and prints Demo ready.

  --port PORT       Factory port (default 43124 or UNIVERSAL_DEMO_PORT)
  --skip-install    Do not run pip
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"
      BASE="http://${HOST}:${PORT}"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown flag: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  python3 -m pip install -e "$ROOT" -q
fi

health_ok() {
  curl -fsS "$BASE/health" >/dev/null 2>&1
}

if health_ok; then
  echo "Using existing factory at $BASE"
else
  echo "Starting universal serve --demo on $BASE"
  mkdir -p "$ROOT/.universal"
  python3 -m universal serve --demo --host "$HOST" --port "$PORT" \
    >"$ROOT/.universal/demo-serve.log" 2>&1 &
  echo $! >"$ROOT/.universal/demo-serve.pid"
  for _ in $(seq 1 40); do
    if health_ok; then
      break
    fi
    sleep 0.15
  done
  if ! health_ok; then
    echo "universal serve did not become healthy. Log: $ROOT/.universal/demo-serve.log" >&2
    exit 1
  fi
fi

create_named() {
  local name="$1"
  local channel="$2"
  local listed
  listed="$(curl -fsS "$BASE/v1/agents")"
  if python3 -c "import json,sys; ids=[a['id'] for a in json.loads(sys.argv[1])['agents'] if a.get('name')==sys.argv[2]]; raise SystemExit(0 if ids else 1)" "$listed" "$name"; then
    python3 -c "import json,sys; print(next(a['id'] for a in json.loads(sys.argv[1])['agents'] if a.get('name')==sys.argv[2]))" "$listed" "$name"
    return
  fi
  curl -fsS "$BASE/v1/agents" \
    -H 'Content-Type: application/json' \
    -d "{\"template\":\"researcher\",\"name\":\"${name}\",\"channel\":\"${channel}\"}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])"
}

RESEARCHER_ID="$(create_named demo-researcher cli)"
HOOK_ID="$(create_named demo-hook webhook)"

cat <<EOF

Demo ready.

  Health     $BASE/health
  Researcher $RESEARCHER_ID  (cli, memory + Tools: utc_now)
  Webhook    $HOOK_ID  (researcher on webhook)

Next (also in DEMO.md):

  # Auto / run
  curl -sS $BASE/v1/agents/$RESEARCHER_ID/run \\
    -H 'Content-Type: application/json' \\
    -d '{"prompt":"What time is it in UTC? Investigate and summarize."}'

  # Webhook inbound
  curl -sS $BASE/v1/agents/$HOOK_ID/webhook \\
    -H 'Content-Type: application/json' \\
    -d '{"text":"hello from another process"}'

  # Browser
  cd web && bun run dev
  open http://127.0.0.1:43123

EOF
