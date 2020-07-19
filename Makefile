VERSION?=0.3
NAMESPACE=chore-nandy-io
.PHONY: install remove reset tag untag

install:
	-kubectl create ns $(NAMESPACE)

remove:
	-kubectl delete ns $(NAMESPACE)

reset: remove instal

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags

untag:
	-git tag -d "v$(VERSION)"
	git push origin ":refs/tags/v$(VERSION)"
