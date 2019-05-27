.PHONY: install update reset remove tag

install:
	kubectl create -f kubernetes/namespace.yaml

update:
	kubectl replace -f kubernetes/namespace.yaml

remove:
	kubectl delete -f kubernetes/namespace.yaml

reset: remove install

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags
