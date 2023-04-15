# Contributing

## Development Environment

use docker

create an env file from the example:

```
cd disocordbot
cp .env.example .env
vim .env
cd ../webapp
cp .env.example .env
vim .env
```

now build and run:

```
make build-webapp
make build-discordbot
make run-discordbot
make run-webapp

curl localhost:8081/guild/<guild id>

firefox http://localhost:8081/embed
```
