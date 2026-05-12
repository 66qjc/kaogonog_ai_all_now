#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/civil.pem}"
SERVER="${SERVER:-ubuntu@150.158.87.179}"
REMOTE_ROOT="${REMOTE_ROOT:-/home/ubuntu/civil}"
REMOTE_LATEST="$REMOTE_ROOT/latest"

SSH_OPTS=(-i "$SSH_KEY")
RSYNC_RSH="ssh -i $SSH_KEY"

cd "$ROOT_DIR/civil-interview-frontend"
npm run build

cd "$ROOT_DIR/civil-interview-miniprogram"
npm run build:mp-weixin:prod

ssh "${SSH_OPTS[@]}" "$SERVER" "mkdir -p '$REMOTE_LATEST/frontend' '$REMOTE_LATEST/miniprogram/mp-weixin-prod'"

rsync -az --delete -e "$RSYNC_RSH" \
  "$ROOT_DIR/civil-interview-frontend/dist/" \
  "$SERVER:$REMOTE_LATEST/frontend/"

rsync -az --delete -e "$RSYNC_RSH" \
  "$ROOT_DIR/civil-interview-miniprogram/dist/build/mp-weixin/" \
  "$SERVER:$REMOTE_LATEST/miniprogram/mp-weixin-prod/"

if [[ "${DEPLOY_BACKEND:-0}" == "1" ]]; then
  LOCAL_BACKEND_ARTIFACT="${LOCAL_BACKEND_ARTIFACT:-/home/quyu/civil/latest/backend}"
  if [[ ! -d "$LOCAL_BACKEND_ARTIFACT" ]]; then
    echo "Missing backend artifact directory: $LOCAL_BACKEND_ARTIFACT" >&2
    exit 1
  fi

  ssh "${SSH_OPTS[@]}" "$SERVER" "mkdir -p '$REMOTE_LATEST/backend'"
  rsync -az --delete -e "$RSYNC_RSH" \
    --exclude='.env' \
    --exclude='.venv/' \
    --exclude='uploads/' \
    --exclude='storage/' \
    "$LOCAL_BACKEND_ARTIFACT/" \
    "$SERVER:$REMOTE_LATEST/backend/"

  ssh "${SSH_OPTS[@]}" "$SERVER" "sudo systemctl restart civil-backend"
fi

ssh "${SSH_OPTS[@]}" "$SERVER" "rm -rf \
  '$REMOTE_ROOT'/.git \
  '$REMOTE_ROOT'/.latest_release_path \
  '$REMOTE_ROOT'/CONFIG_DECRYPTION_KEY_* \
  '$REMOTE_ROOT'/civil_release_* \
  '$REMOTE_ROOT'/frontend \
  '$REMOTE_ROOT'/miniprogram \
  '$REMOTE_LATEST'/OPS_MANUAL.md \
  '$REMOTE_LATEST'/README_DEPLOY.md \
  '$REMOTE_LATEST'/操作手册_部署运维_MySQL_ONLY.md \
  '$REMOTE_LATEST'/ai_gongwu_backend \
  '$REMOTE_LATEST'/config \
  '$REMOTE_LATEST'/data \
  '$REMOTE_LATEST'/frontend_h5 \
  '$REMOTE_LATEST'/logs \
  '$REMOTE_LATEST'/scripts \
  '$REMOTE_LATEST'/miniprogram/README_MINI.md \
  '$REMOTE_LATEST'/miniprogram/mp-weixin \
  '$REMOTE_LATEST'/miniprogram/mp-weixin-dev \
  '$REMOTE_LATEST'/backend/.env.bak.* \
  '$REMOTE_LATEST'/backend/.env.enc \
  '$REMOTE_LATEST'/backend/.env_example \
  '$REMOTE_LATEST'/backend/__pycache__ \
  '$REMOTE_LATEST'/backend/app/__pycache__"

ssh "${SSH_OPTS[@]}" "$SERVER" "if grep -Eq '^DATABASE_URL=(mysql|mysql\\+)' '$REMOTE_LATEST/backend/.env'; then rm -f '$REMOTE_LATEST/backend/'*.db; fi"

ssh "${SSH_OPTS[@]}" "$SERVER" "sudo nginx -t && for i in {1..20}; do curl -fsS http://127.0.0.1:8050/health >/dev/null && exit 0; sleep 1; done; curl -fsS http://127.0.0.1:8050/health >/dev/null"
for i in {1..20}; do
  curl -fsS https://xzqianmianyuzhoukeji.com/api/health >/dev/null && break
  sleep 1
  if [[ "$i" == "20" ]]; then
    curl -fsS https://xzqianmianyuzhoukeji.com/api/health >/dev/null
  fi
done

echo "Clean deploy finished."
