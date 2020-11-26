cd ..
python3 webserv.py ./testconfigs/config1.cfg &
PID=$!
cd -
curl -I 127.0.0.1:8070/hello.html 2> /dev/null | grep '200 OK' | diff - hello_static.out 
kill $PID
