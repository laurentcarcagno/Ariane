#!/bin/bash
# Creates the "ariane-web" OIDC client (public, Authorization Code + PKCE) in the shared realm, with the two mappers the API
# needs: audience "ariane-api" and the "customer" claim (user attribute). Declares the attribute in the realm's user profile
# (Keycloak 26 drops undeclared attributes) and sets it for ARIANE_CUSTOMER_USERS. Idempotent.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
REALM=${KEYCLOAK_REALM:-infra}
CLIENT=ariane-web
need_keycloak_admin

[ -n "$(kc get "realms/$REALM" --fields realm --format csv --noquotes 2>/dev/null)" ] || { echo "realm $REALM does not exist in Keycloak" >&2; exit 1; }

# 1. user-profile attribute "customer" (admin-editable only: a user must not choose its own customer)
PROFILE=$(kc get "users/profile" -r "$REALM")
if ! grep -q '"name" *: *"customer"' <<<"$PROFILE"; then
  python3 -c '
import json,sys
p=json.load(sys.stdin)
p["attributes"].append({"name":"customer","displayName":"Customer","permissions":{"view":["admin"],"edit":["admin"]},"multivalued":False})
json.dump(p,sys.stdout)' <<<"$PROFILE" | $PODMAN exec -i "${KEYCLOAK_CONTAINER:-keycloak}" sh -c 'cat > /tmp/profile.json'
  kc update "users/profile" -r "$REALM" -f /tmp/profile.json >/dev/null
  echo "user-profile attribute customer declared"
fi

# 2. client
if [ -z "$(kc get clients -r "$REALM" -q clientId=$CLIENT --fields id --format csv --noquotes)" ]; then
  kc create clients -r "$REALM" -s clientId=$CLIENT -s enabled=true -s protocol=openid-connect \
    -s publicClient=true -s standardFlowEnabled=true -s directAccessGrantsEnabled=false \
    -s 'attributes."pkce.code.challenge.method"=S256' >/dev/null
  echo "client $CLIENT created"
fi
CID=$(kc get clients -r "$REALM" -q clientId=$CLIENT --fields id --format csv --noquotes)
kc update "clients/$CID" -r "$REALM" -s "redirectUris=[\"${ARIANE_URL}/*\"]" -s "webOrigins=[\"${ARIANE_URL}\"]" \
  -s "attributes.\"post.logout.redirect.uris\"=${ARIANE_URL}/*" >/dev/null

# 3. mappers
MAPPERS=$(kc get "clients/$CID/protocol-mappers/models" -r "$REALM" --fields name --format csv --noquotes)
grep -qx audience-ariane-api <<<"$MAPPERS" || \
  kc create "clients/$CID/protocol-mappers/models" -r "$REALM" -s name=audience-ariane-api -s protocol=openid-connect \
    -s protocolMapper=oidc-audience-mapper -s 'config."included.custom.audience"=ariane-api' \
    -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=false' >/dev/null
grep -qx customer <<<"$MAPPERS" || \
  kc create "clients/$CID/protocol-mappers/models" -r "$REALM" -s name=customer -s protocol=openid-connect \
    -s protocolMapper=oidc-usermodel-attribute-mapper -s 'config."user.attribute"=customer' \
    -s 'config."claim.name"=customer' -s 'config."jsonType.label"=String' \
    -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=true' -s 'config."userinfo.token.claim"=true' >/dev/null

# 4. customers of the listed users
for pair in ${ARIANE_CUSTOMER_USERS:-}; do
  user=${pair%%=*}; customer=${pair#*=}
  uid=$(kc get users -r "$REALM" -q username="$user" -q exact=true --fields id --format csv --noquotes)
  [ -n "$uid" ] || { echo "user $user not found in $REALM" >&2; continue; }
  kc update "users/$uid" -r "$REALM" -s "attributes.customer=[\"$customer\"]" >/dev/null
  echo "user $user -> customer $customer"
done
echo "Keycloak client $CLIENT ready in realm $REALM (redirect ${ARIANE_URL}/*)"
