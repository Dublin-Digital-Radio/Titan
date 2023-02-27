build-discordbot:
	 docker build --build-arg GIT_COMMIT=$$(git rev-parse HEAD) -t discordbot --target discordbot .

build-webapp:
	 docker build --build-arg GIT_COMMIT=$$(git rev-parse HEAD) -t titan-webapp --target webapp .

build-all: build-discordbot build-webapp

run-discordbot:
	docker run --env-file discordbot/.env --network host discordbot

run-webapp:
	docker run --env-file webapp/.env --network host titan-webapp

deploy-webapp:
	flyctl deploy --env GIT_COMMIT=$$(git rev-parse HEAD) --build-target webapp --config webapp/fly.toml

deploy-webapp-remote:
	flyctl deploy --remote-only --env GIT_COMMIT=$$(git rev-parse HEAD) --build-target webapp --config webapp/fly.toml

deploy-discordbot:
	 flyctl deploy --env GIT_COMMIT=$$(git rev-parse HEAD) --build-target discordbot --config discordbot/fly.toml

deploy-discordbot-remote:
	 flyctl deploy --remote-only --env GIT_COMMIT=$$(git rev-parse HEAD) --build-target discordbot --config discordbot/fly.toml

ssh-webapp:
	flyctl ssh console --config webapp/fly.toml --app ddr-titan

ssh-discordbot:
	flyctl ssh console --config discordbot/fly.toml --app ddr-discord-bot

logs-webapp:
	flyctl logs --app ddr-titan

logs-discordbot:
	flyctl logs --app ddr-discord-bot

deploy-all: deploy-discordbot deploy-webapp

pip-install-discordbot:
	pip install -r discordbot/requirements.txt

pip-install-webapp:
	pip install -r webapp/requirements.txt

make-discordbot-venv:
	python3 -mvenv ../venvs/discordbot
	../venvs/discordbot/bin/activate
	pip install -r discordbot/requirements.txt
	 pip install -r requirements.dev.txt

make-webapp-venv:
	python3 -mvenv ../venvs/Titan-webapp
	../venvs/Titan-webapp/bin/activate
	pip install -r webapp/requirements.txt
	 pip install -r requirements.dev.txt

rm-discordbot-venv:
	deactivate
	rm -r ../venvs/discordbot/bin/activate

rm-webapp-venv:
	deactivate
	rm -r ../venvs/Titan-webapp/bin/activate

restart-discordbot:
	fly apps restart ddr-discord-bot

restart-webapp:
	fly apps restart ddr-titan
