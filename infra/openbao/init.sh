#!/bin/sh
# One-shot bootstrap of OpenBao: init, unseal, KV v2, AppRole for the API, seed secrets.
# DEV/POC ONLY for the unseal key: it is kept in a volume so the stack restarts unattended.
# In production use several key shares held by different people and remove /openbao/init.
set -eu

export BAO_ADDR="${BAO_ADDR:-http://openbao:8200}"
INIT=/openbao/init/init.json
OUT=/openbao/approle

until bao status -format=json >/dev/null 2>&1 || [ $? -eq 2 ]; do sleep 1; done

if [ "$(bao status -format=json 2>/dev/null | grep -c '"initialized": true')" -eq 0 ]; then
  mkdir -p /openbao/init
  bao operator init -key-shares=1 -key-threshold=1 -format=json > "$INIT"
  chmod 600 "$INIT"
fi

UNSEAL_KEY=$(sed -n 's/.*"unseal_keys_b64": \[ *"\([^"]*\)".*/\1/p' "$INIT" | head -1)
[ -n "$UNSEAL_KEY" ] || UNSEAL_KEY=$(tr -d '\n ' < "$INIT" | sed -n 's/.*"unseal_keys_b64":\["\([^"]*\)".*/\1/p')
if bao status -format=json | grep -q '"sealed": true'; then bao operator unseal "$UNSEAL_KEY" >/dev/null; fi

export BAO_TOKEN=$(tr -d '\n ' < "$INIT" | sed -n 's/.*"root_token":"\([^"]*\)".*/\1/p')

bao secrets list -format=json | grep -q '"secret/"' || bao secrets enable -path=secret -version=2 kv
bao policy write ariane-backend /openbao/policy-ariane-backend.hcl
bao auth list -format=json | grep -q '"approle/"' || bao auth enable approle
bao write auth/approle/role/ariane-backend token_policies=ariane-backend token_ttl=15m token_max_ttl=1h secret_id_ttl=0 >/dev/null

# secrets the API reads at start-up (idempotent: existing values are kept)
if ! bao kv get secret/ariane >/dev/null 2>&1; then
  bao kv put secret/ariane DB_PASSWORD="${ARIANE_DB_PASSWORD:?ARIANE_DB_PASSWORD is required}" >/dev/null
fi

mkdir -p "$OUT"
bao read -field=role_id auth/approle/role/ariane-backend/role-id > "$OUT/role_id"
bao write -f -field=secret_id auth/approle/role/ariane-backend/secret-id > "$OUT/secret_id"
chmod 644 "$OUT/role_id" "$OUT/secret_id"
echo "openbao ready"
