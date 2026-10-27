#!/bin/bash
# Deploys ARIANE with Podman on the INFRA platform.
#
#   ./deploy.sh [STEP...]        run on the target server (default: keycloak openbao build up proxy)
#
# Steps:
#   keycloak  creates/updates the OIDC client "ariane-web", the "customer" claim and the customers of ARIANE_CUSTOMER_USERS
#   openbao   creates secret/ariane, its policy and AppRole; writes their credentials into the env file
#   build     builds the backend and frontend images
#   up        starts (or restarts) the stack
#   proxy     adds the ariane.<domain> route to the INFRA Caddyfile (once) and restarts the proxy (admin API is off)
#
# Option:   -e FILE   site configuration (default: deploy/.env, from .env.example)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HERE/.env"; STEPS=()
while [ $# -gt 0 ]; do
  case "$1" in
    -e) ENV_FILE=$(realpath "$2"); shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) STEPS+=("$1"); shift ;;
  esac
done
[ ${#STEPS[@]} -gt 0 ] || STEPS=(keycloak openbao build up proxy)

[ -f "$ENV_FILE" ] || { cp "$HERE/.env.example" "$ENV_FILE"; chmod 600 "$ENV_FILE"; echo "created $ENV_FILE from .env.example"; }
export ENV_FILE
. "$HERE/lib.sh"
cd "$HERE"
if [ -z "${ARIANE_DB_PASSWORD:-}" ]; then
  ARIANE_DB_PASSWORD=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))'); set_env ARIANE_DB_PASSWORD "$ARIANE_DB_PASSWORD"
  export ARIANE_DB_PASSWORD
fi

case "$PODMAN" in sudo*) COMPOSE=${COMPOSE:-sudo podman-compose} ;; *) COMPOSE=${COMPOSE:-podman-compose} ;; esac
# own project name: the directory name ("deploy") collides with other stacks on the host
compose(){ $COMPOSE -p ariane --env-file "$ENV_FILE" -f "$HERE/compose.yaml" "$@"; }

for step in "${STEPS[@]}"; do
  echo "=== $step"
  case "$step" in
    keycloak) "$HERE/configure-keycloak.sh" ;;
    openbao)  "$HERE/configure-openbao.sh" ;;
    build)    compose build ;;
    up)       . "$ENV_FILE"   # pick up the credentials written by the openbao step
              compose down >/dev/null 2>&1 || true   # recreate the containers (the data volume is kept)
              compose up -d ;;
    proxy)    host=${ARIANE_URL#*://}
              caddyfile="$INFRA_DIR/proxy/Caddyfile"
              if ! grep -q "BEGIN ariane " "$caddyfile"; then
                cat >> "$caddyfile" <<ROUTE

# BEGIN ariane (managed by ARIANE deploy/deploy.sh)
$host {
	request_body {
		max_size 60MB
	}
	handle /api/* {
		reverse_proxy ariane-backend:8000
	}
	handle {
		reverse_proxy ariane-frontend:3000
	}
}
# END ariane
ROUTE
                echo "route $host added to $caddyfile"
              fi
              $PODMAN restart "${PROXY_CONTAINER:-proxy}" >/dev/null && echo "proxy restarted" ;;
    *) echo "unknown step: $step" >&2; exit 1 ;;
  esac
done
