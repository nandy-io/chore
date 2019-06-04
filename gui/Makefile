MACHINE=$(shell uname -m)
ACCOUNT=nandyio
IMAGE=chore-gui
VERSION=0.1
NAME=$(IMAGE)-$(ACCOUNT)
NETWORK=klot.io
VOLUMES=-v ${PWD}/www/:/opt/nandy-io/www/ \
		-v ${PWD}/etc/docker.conf:/etc/nginx/conf.d/default.conf
PORT=6771

ifeq ($(MACHINE),armv7l)
BASE=arm32v7/nginx
else
BASE=nginx:1.15.7-alpine
endif

.PHONY: cross build network shell run start stop push install update remove reset tag

cross:
	docker run --rm --privileged multiarch/qemu-user-static:register --reset

build:
	docker build . --build-arg BASE=$(BASE) -t $(ACCOUNT)/$(IMAGE):$(VERSION)

network:
	-docker network create $(NETWORK)

shell: network
	-docker run -it --rm --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh

run: network
	docker run --rm --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) -p 127.0.0.1:$(PORT):80 --expose=80 $(ACCOUNT)/$(IMAGE):$(VERSION)

start: network
	docker run -d --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) -p 127.0.0.1:$(PORT):80 --expose=80 $(ACCOUNT)/$(IMAGE):$(VERSION)

stop:
	docker rm -f $(NAME)

push:
ifeq ($(MACHINE),armv7l)
	docker push $(ACCOUNT)/$(IMAGE):$(VERSION)
else
	echo "Only push armv7l"
endif

install:
	kubectl create -f kubernetes/gui.yaml

update:
	kubectl replace -f kubernetes/gui.yaml

remove:
	-kubectl delete -f kubernetes/gui.yaml

reset: remove install

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags
