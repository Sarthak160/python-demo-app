# Purpose Advisors Demo

curl -X POST \  
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \            
  http://localhost:5000/login





### Dedup
keploy test -c "python3 demo.py" --dedup -t test-set-0 --freezeTime

### Rerecord
 keploy rerecord -c "sudo docker run --network keploy-network -p 5000:5000 --name flask-jwt-test --rm flask-keploy-app" # python-demo-app
