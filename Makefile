dev-setup:
	poetry install
	poetry run pre-commit install

dev-container-run:
	docker run -d \
	--name homeassistant \
	--privileged \
	--restart=unless-stopped \
	-e TZ=UTC \
	-v ./.devcontainer:/config \
	-v ./custom_components:/config/custom_components \
	-v /run/dbus:/run/dbus:ro \
	-p 9123:8123 \
	ghcr.io/home-assistant/home-assistant:stable
	echo http://localhost:9123

dev-container-rm:
	docker container stop homeassistant
	docker container rm homeassistant
