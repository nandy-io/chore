ACCOUNT=nandyio
IMAGE=chore-daemon
VERSION?=0.1
NAME=$(IMAGE)-$(ACCOUNT)
NETWORK=klot.io
VOLUMES=-v ${PWD}/lib/:/opt/service/lib/ \
		-v ${PWD}/bin/:/opt/service/bin/ \
		-v ${PWD}/test/:/opt/service/test/
ENVIRONMENT=-e SLEEP=5 \
			-e CHORE_API=http://chore-api.nandyio

.PHONY: cross build network shell test run start stop push install update remove reset tag

cross:
	docker run --rm --privileged multiarch/qemu-user-static:register --reset

build:
	docker build . -t $(ACCOUNT)/$(IMAGE):$(VERSION)

network:
	-docker network create klot-io

shell: kube network
	-docker run -it --rm --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh

test:
	docker run -it $(VOLUMES) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "coverage run -m unittest discover -v test && coverage report -m --include lib/*.py"

run: kube network
	docker run --rm --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION)

start: network
	docker run -d --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION)

stop:
	docker rm -f $(NAME)

push:
	docker push $(ACCOUNT)/$(IMAGE):$(VERSION)

install:
	kubectl create -f kubernetes/daemon.yaml

update:
	kubectl replace -f kubernetes/daemon.yaml

remove:
	-kubectl delete -f kubernetes/daemon.yaml

reset: remove install

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags
