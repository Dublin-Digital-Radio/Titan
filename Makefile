build-discordbot:
	 docker build -t discordbot --target discordbot .

build-webapp:
	 docker build -t titan-webapp --target webapp .

build-all: build-discordbot build-webapp

run-discordbot:
	docker run --env-file discordbot/.env --network host discordbot

run-webapp:
	docker run --env-file webapp/.env --network host titan-webapp

deploy-webapp:
	flyctl deploy  --build-target webapp --config webapp/fly.toml

deploy-discordbot:
	 flyctl deploy  --build-target discordbot --config discordbot/fly.toml

deploy-all: deploy-bot deploy-webapp

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
