cd ..
python3 webserv.py ./testconfigs/config1.cfg &
PID=$!
cd -
curl localhost:8070/nihao.txt | diff - nihao_test.out 
kill $PID