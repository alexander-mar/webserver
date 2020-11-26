cd ..
python3 webserv.py ./testconfigs/config8.cfg &
PID=$!
cd -
python3 ../webserv.py | diff - nonexistent_config.out
kill $PID
