# Shared by the deploy scripts: loads deploy/.env and defines the helpers.
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set -a; . "${ENV_FILE:-$DEPLOY_DIR/.env}"; set +a
PODMAN=${PODMAN:-sudo podman}
INFRA_DIR=${INFRA_DIR:-}

# kc ARGS...: Keycloak admin CLI inside the Keycloak container
kc(){ $PODMAN exec "${KEYCLOAK_CONTAINER:-keycloak}" /opt/keycloak/bin/kcadm.sh "$@"; }
# bao ARGS...: OpenBao CLI inside the OpenBao container, with the root token
bao(){ $PODMAN exec -i -e BAO_TOKEN="$OPENBAO_ROOT_TOKEN" "${OPENBAO_CONTAINER:-openbao}" bao "$@"; }

need_keycloak_admin() {
  if [ -z "${KEYCLOAK_ADMIN_PASSWORD:-}" ] && [ -f "$INFRA_DIR/.env" ]; then
    KEYCLOAK_ADMIN_PASSWORD=$(grep -m1 '^ADMIN_PASSWORD=' "$INFRA_DIR/.env" | cut -d= -f2-)
  fi
  : "${KEYCLOAK_ADMIN_PASSWORD:?set KEYCLOAK_ADMIN_PASSWORD in deploy/.env or the environment}"
  kc config credentials --server "http://localhost:8080" --realm master \
    --user "${KEYCLOAK_ADMIN_USER:-admin}" --password "$KEYCLOAK_ADMIN_PASSWORD" >/dev/null
}

need_openbao_root() {
  if [ -z "${OPENBAO_ROOT_TOKEN:-}" ] && [ -f "$INFRA_DIR/secrets/openbao-init.json" ]; then
    OPENBAO_ROOT_TOKEN=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['root_token'])" "$INFRA_DIR/secrets/openbao-init.json")
  fi
  : "${OPENBAO_ROOT_TOKEN:?set OPENBAO_ROOT_TOKEN in deploy/.env or the environment}"
}

# set_env KEY VALUE: update a key of deploy/.env
set_env() {
  local file="${ENV_FILE:-$DEPLOY_DIR/.env}"
  if grep -q "^$1=" "$file"; then sed -i "s|^$1=.*|$1=$2|" "$file"; else echo "$1=$2" >> "$file"; fi
}
