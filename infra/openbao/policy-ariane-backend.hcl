# The API may read its own secrets, nothing else.
path "secret/data/ariane" {
  capabilities = ["read"]
}
