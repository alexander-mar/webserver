cd ..
python3 webserv.py ./testconfigs/config1.cfg &
PID=$!
cd -
curl -I 127.0.0.1:8070/missing.html 2> /dev/null | grep '404' | diff - 404_test.out 
kill $PID