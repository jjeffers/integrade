oc rsh -c cloudigrade-api $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=cloudigrade-api) scl enable rh-postgresql96 rh-python36 -- python manage.py $*
