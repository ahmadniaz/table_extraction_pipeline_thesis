#!/bin/bash

# Docker test script for commission tracker backend
echo "🐳 Testing Docker build for commission tracker backend..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t commission-tracker-backend .

if [ $? -eq 0 ]; then
    echo "✅ Docker build successful!"
    
    # Run the container
    echo "🚀 Starting container..."
    docker run -d --name commission-tracker-test -p 8000:8000 commission-tracker-backend
    
    if [ $? -eq 0 ]; then
        echo "✅ Container started successfully!"
        echo "🌐 Application should be available at: http://localhost:8000"
        echo "🏥 Health check endpoint: http://localhost:8000/health"
        echo "📚 API documentation: http://localhost:8000/docs"
        
        # Wait a moment for the app to start
        echo "⏳ Waiting for application to start..."
        sleep 5
        
        # Test the health endpoint
        echo "🔍 Testing health endpoint..."
        curl -f http://localhost:8000/health
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "🎉 All tests passed! Your Docker container is running successfully."
            echo ""
            echo "To stop the container, run:"
            echo "  docker stop commission-tracker-test"
            echo "  docker rm commission-tracker-test"
            echo ""
            echo "To view logs, run:"
            echo "  docker logs commission-tracker-test"
        else
            echo "❌ Health check failed. Check the logs with: docker logs commission-tracker-test"
        fi
    else
        echo "❌ Failed to start container"
    fi
else
    echo "❌ Docker build failed"
    exit 1
fi 