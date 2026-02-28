cd ./frontend && npm run build

echo "Frontend build completed."

# Return to the root directory
cd ..
echo "Build process finished."
docker build --platform "$TARGETPLATFORM" -t lite-llm-proxy:latest .

docker-compose up -d