.PHONY: install update reset remove

install:
	kubectl create -f kubernetes/namespace.yaml

update:
	kubectl replace -f kubernetes/namespace.yaml

remove:
	kubectl delete -f kubernetes/namespace.yaml

reset: remove install
