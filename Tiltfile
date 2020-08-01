docker_build('gui-chore-nandy-io', './gui')
docker_build('api-chore-nandy-io', './api')
docker_build('daemon-chore-nandy-io', './daemon')

k8s_yaml(kustomize('.'))

k8s_resource('gui', port_forwards=['6567:80'])
k8s_resource('mysql', port_forwards=['6535:5678'])
k8s_resource('api', port_forwards=['16567:80', '16535:5678'])
k8s_resource('daemon', port_forwards=['26535:5678'])
