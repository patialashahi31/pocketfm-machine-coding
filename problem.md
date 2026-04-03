Build a centralized rate limiter that any service can call to check if a request should be allowed.

Distributed
In Memory/ Redis
Algorithm - 2 algos
Configurations


Decisions - 

- We need redis as data store to store rate limits
- Algo to use - Fixed window
- Lets go ahead with json static config
- FastAPI service. 
Redis , Rate limiter

Task 1 - Sample API service built on Fast API: 
- This is just a sample one, not rate limiter. 
- Just create 2 normal APIs, without any state maintained
- No DB
- Create a new folder in current folder
- Dockerfile 

Task 2: 
- Rate limiting service
- Create a new folder in current folder
- FastAPI service with 2 APIs
- Dockerfile 

Task 3: 
- docker-compose.yml in current folder
- Services should be - redis, ratelimiting service, sample fast api service

Task 4:
Create a makefile for shortcuts like docker compose up

Task 5
- Lets create a load generator service to create load on our sample service
- We can use k6 docker container
- Create a make command to create and test the load


Redis

- RDB 