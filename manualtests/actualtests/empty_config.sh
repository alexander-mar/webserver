cd ..
python3 webserv.py ./testconfigs/config2.cfg &
PID=$!
cd -
python3 ../webserv.py | diff - empty_config.out
kill $PID
