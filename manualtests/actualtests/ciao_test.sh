cd ..
python3 webserv.py ./testconfigs/config1.cfg &
PID=$!
cd -
curl localhost:8070/ciao.js | diff - ciao_static.out 
kill $PID