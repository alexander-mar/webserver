cd ..
python3 webserv.py ./testconfigs/config1.cfg &
PID=$!
cd -
curl localhost:8070/cgibin/hi.java | diff - hi_cgi.out
kill $PID
