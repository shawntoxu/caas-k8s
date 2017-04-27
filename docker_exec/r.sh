curl --silent --unix-socket /var/run/docker.sock "http:/exec/3fe18148e3c4c75bf39dcb8c8e56055dec206439a4adfc6cfa6502418ef68760/start" -XPOST \
  -H "Content-Type: application/json" \
  -d '{
    "Detach": false,
    "Tty": true
  }'
