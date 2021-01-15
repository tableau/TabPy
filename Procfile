web: export TABPY_PORT=$PORT 
web: tabpy& 
web: sed -i "s/# TABPY_PORT = 9004/TABPY_PORT=$PORT/" /app/tabpy/tabpy_server/common/default.conf
web: tabpy-deploy-models default.conf
