docker build -t cromwell-tools:test ../..

# Run unit tests in docker container
docker run --entrypoint python3 cromwell-tools:test -m unittest discover -v