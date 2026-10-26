ui = true
api_addr = "http://openbao:8200"

storage "file" {
  path = "/openbao/file"
}

# Plain HTTP stays inside the compose network; nothing publishes this port.
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}
