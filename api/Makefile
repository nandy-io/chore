ACCOUNT=nandyio
IMAGE=chore-api
VERSION=0.2
NAME=$(IMAGE)-$(ACCOUNT)
NETWORK=klot.io
NETWORK=chore.nandy.io
MYSQL_IMAGE=klotio/mysql:0.3
MYSQL_HOST=$(ACCOUNT)-$(IMAGE)-mysql
DEBUG_PORT=16535
TTY=$(shell if tty -s; then echo "-it"; fi)
VOLUMES=-v ${PWD}/lib/:/opt/service/lib/ \
		-v ${PWD}/bin/:/opt/service/bin/ \
		-v ${PWD}/test/:/opt/service/test/ \
		-v ${PWD}/mysql.sh:/opt/service/mysql.sh \
		-v ${PWD}/.pylintrc:/opt/service/.pylintrc
ENVIRONMENT=-e MYSQL_HOST=$(MYSQL_HOST) \
			-e MYSQL_PORT=3306 \
			-e PYTHONDONTWRITEBYTECODE=1 \
			-e PYTHONUNBUFFERED=1

.PHONY: cross build network shell debug test lint push install update remove reset

cross:
	docker run --rm --privileged multiarch/qemu-user-static:register --reset

build:
	docker build . -t $(ACCOUNT)/$(IMAGE):$(VERSION)

network:
	-docker network create $(NETWORK)

mysql: network
	-docker rm --force $(MYSQL_HOST)
	docker run -d --network=$(NETWORK) -h $(MYSQL_HOST) --name=$(MYSQL_HOST) -e MYSQL_ALLOW_EMPTY_PASSWORD='yes' $(MYSQL_IMAGE)
	docker run $(TTY) --rm --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "./mysql.sh"

shell: mysql
	docker run $(TTY) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh
	docker rm --force $(MYSQL_HOST)

debug: mysql
	docker run $(TTY) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) -p 127.0.0.1:$(DEBUG_PORT):5678 $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "python -m ptvsd --host 0.0.0.0 --port 5678 --wait -m unittest discover -v test"
	docker rm --force $(MYSQL_HOST)

test: mysql
	docker run $(TTY) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "coverage run -m unittest discover -v test && coverage report -m --include 'lib/*.py'"
	docker rm --force $(MYSQL_HOST)

lint:
	docker run $(TTY) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "pylint --rcfile=.pylintrc lib/"

push:
	docker push $(ACCOUNT)/$(IMAGE):$(VERSION)

install:
	kubectl create -f kubernetes/mysql.yaml
	kubectl create -f kubernetes/api.yaml

update:
	kubectl replace -f kubernetes/mysql.yaml
	kubectl replace -f kubernetes/api.yaml

remove:
	-kubectl delete -f kubernetes/api.yaml
	-kubectl delete -f kubernetes/mysql.yaml

reset: remove install
