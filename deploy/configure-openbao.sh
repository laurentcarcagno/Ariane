#!/bin/bash
# Gives ARIANE its secret in OpenBao: KV v2 secret/ariane (DB_PASSWORD, never overwritten), a read-only policy and an AppRole.
# Writes OPENBAO_ROLE_ID / OPENBAO_SECRET_ID into deploy/.env (a new secret_id is issued each time). Re-runnable.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
need_openbao_root
: "${ARIANE_DB_PASSWORD:?run ./deploy.sh (it generates ARIANE_DB_PASSWORD)}"

bao secrets list -format=json | grep -q '"secret/"' || bao secrets enable -path=secret -version=2 kv
bao auth list -format=json | grep -q '"approle/"' || bao auth enable approle

bao policy write ariane - <<'POL' >/dev/null
path "secret/data/ariane" { capabilities = ["read"] }
POL
bao write auth/approle/role/ariane token_policies=ariane token_ttl=15m token_max_ttl=1h >/dev/null

bao kv get -mount=secret ariane >/dev/null 2>&1 || bao kv put -mount=secret ariane DB_PASSWORD="$ARIANE_DB_PASSWORD" >/dev/null

set_env OPENBAO_ROLE_ID "$(bao read -field=role_id auth/approle/role/ariane/role-id)"
set_env OPENBAO_SECRET_ID "$(bao write -f -field=secret_id auth/approle/role/ariane/secret-id)"
echo "OpenBao ready: secret/ariane, AppRole ariane (credentials written to the env file)"
