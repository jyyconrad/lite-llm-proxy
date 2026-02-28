
# LiteLLM API Gateway - Complete Implementation

A comprehensive API gateway built on LiteLLM that provides unified model management, usage tracking, account management, and concurrency control for multiple LLM providers.

## 🚀 Core Features

### 1. Model Unified Management
- **100+ Model Support**: Configure and manage models from multiple providers (OpenAI, Anthropic, Azure, Ollama, etc.)
- **Unified Interface**: Single API endpoint for all model interactions
- **Model Routing**: Intelligent routing based on model configuration
- **Rate Limiting**: Per-model RPM (Requests Per Minute) and TPM (Tokens Per Minute) limits
- **Web Management Interface**: Complete model configuration and monitoring dashboard

### 2. Usage Statistics System
- **Real-time Tracking**: Track calls, tokens, and costs per user and per model
- **Cost Calculation**: Automatic cost calculation using LiteLLM's pricing data
- **Usage Analytics**: Comprehensive usage statistics and reporting
- **Budget Monitoring**: Real-time budget tracking and alerts
- **Visual Dashboard**: Interactive charts and statistics visualization

### 3. Account Management System
- **User Management**: Create and manage user accounts with roles
- **API Key Generation**: Secure API key generation and management
- **Role-Based Access Control**: Admin and user roles with appropriate permissions
- **Budget Controls**: Per-user budget limits and spending caps
- **Rate Limiting**: Configurable RPM and TPM limits per user (set to -1 for no limits)

### 4. Concurrency Control Mechanism
- **Rate Limiting**: Configurable RPM limits per user and per model
- **Token Rate Limits**: TPM limits to control token consumption
- **Budget Enforcement**: Automatic blocking when budget limits are reached
- **Redis-Based Counters**: Efficient rate limiting with Redis

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │ ── │  API Gateway     │ ── │  LLM Providers  │
│                 │    │  (FastAPI)       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                      ┌───────┼───────┐
                      │       │       │
                ┌─────▼─┐ ┌──▼──┐ ┌──▼──┐
                │PostgreSQL │ │ Redis │ │LiteLLM│
                │Database   │ │Cache  │ │Config │
                └──────────┘ └──────┘ └───────┘
```

## 📋 API Endpoints

### User Management
- `POST /users` - Create new user account
- `POST /api-keys` - Generate API key for user
- `GET /usage/{user_id}` - Get usage statistics for user

### Model Management
- `GET /models` - List all available models

### Model Inference
- `POST /completions` - Make completion requests to any model

### Statistics & Monitoring
- `GET /admin/stats` - Get admin-level statistics (admin only)
- `GET /admin/stats/overview` - System overview statistics
- `GET /admin/stats/model-usage` - Model usage statistics
- `GET /admin/stats/recent-activity` - Recent activity records
- `GET /admin/stats/user/{user_id}` - User detailed statistics
- `GET /stats/usage` - User self-service statistics

### Health & Monitoring
- `GET /health` - Health check endpoint
- `GET /docs` - API documentation (Swagger UI)

## 🔧 Configuration

### Model Configuration (`litellm_config.yaml`)
```yaml
model_list:
  - model_name: "gpt-4o"
    litellm_params:
      model: "gpt-4o"
      api_key: "os.environ/OPENAI_API_KEY"
    rpm: 60
    tpm: 60000
    model_info:
      description: "OpenAI GPT-4 Omni model"
      max_tokens: 128000
      provider: "openai"
```

### Environment Variables
Create a `.env` file with the following variables:
```bash
# API Gateway Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/litellm_gateway
REDIS_URL=redis://localhost:6379
MASTER_KEY=sk-lite-llm-gateway-2025

# LLM Provider API Keys
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
AZURE_OPENAI_ENDPOINT=your-azure-endpoint-here
AZURE_OPENAI_KEY=your-azure-key-here

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Rate Limiting Configuration
DEFAULT_RPM_LIMIT=60
DEFAULT_TPM_LIMIT=60000
DEFAULT_BUDGET_LIMIT=1000.0

# Security Configuration
JWT_SECRET=your-jwt-secret-key-here
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)
```bash
# Set your API keys
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"

# Start all services
docker-compose up -d

# Access the application
# API Gateway: http://localhost:8000
# Web Dashboard: Open web_dashboard.html in browser
# API Documentation: http://localhost:8000/docs
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start services manually
docker run -d -p 5432:5432 --name postgres postgres:15
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Initialize database
python database_migration.py migrate

# Run the API gateway
python api_gateway.py
```

## 🧪 Testing

### Core Functionality Tests
```bash
python test_gateway.py
```

### Integration Tests
```bash
python integration_tests.py
```

### Dashboard Endpoint Tests
```bash
python test_dashboard_endpoints.py
```

### Production Deployment Tests
```bash
python test_production_deployment.py
```

## 📊 Usage Examples

### Create a User
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "budget_limit": 1000.0,
    "rpm_limit": 60,
    "tpm_limit": 60000
  }'
```

### Generate API Key
```bash
curl -X POST http://localhost:8000/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "description": "Test API Key"
  }'
```

### Make Completion Request
```bash
curl -X POST http://localhost:8000/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

### Check Usage Statistics
```bash
curl -X GET http://localhost:8000/usage/user-uuid \
  -H "Authorization: Bearer your-api-key"
```

### Access Dashboard Statistics
```bash
curl -X GET http://localhost:8000/admin/stats/overview \
  -H "Authorization: Bearer admin-api-key"
```

## 🖥️ Web Dashboard

The project includes a comprehensive web dashboard for system management:

- **Real-time Statistics**: View system usage, costs, and performance metrics
- **User Management**: Manage users, roles, and API keys
- **Model Configuration**: Configure and monitor model settings
- **Usage Analytics**: Interactive charts and reports

To access the dashboard, open `web_dashboard.html` in your web browser.

## 🔒 Security Features

- **API Key Authentication**: Bearer token authentication for all endpoints
- **Rate Limiting**: Configurable limits to prevent abuse
- **Budget Controls**: Automatic spending limits
- **Role-Based Access**: Admin and user roles with appropriate permissions
- **Input Validation**: Pydantic models for request validation
- **CORS Protection**: Configurable CORS settings

## 📈 Monitoring & Analytics

The system provides comprehensive monitoring through:

1. **Real-time Usage Tracking**: Per-user and per-model statistics
2. **Cost Analytics**: Detailed cost breakdowns
3. **Performance Metrics**: Response times and success rates
4. **Admin Dashboard**: Overall system statistics
5. **Health Monitoring**: Service health checks and status monitoring

## 🛠️ Technical Stack

- **Backend**: FastAPI (Python)
- **Model Proxy**: LiteLLM
- **Database**: PostgreSQL
- **Cache**: Redis
- **Frontend**: Vue 3 + Tailwind CSS
- **Containerization**: Docker & Docker Compose
- **Authentication**: API Key-based with RBAC
- **Monitoring**: Prometheus + Grafana (optional)

## 🔄 Extensibility

The architecture is designed to be easily extensible:

- Add new model providers by updating `litellm_config.yaml`
- Implement custom rate limiting algorithms
- Add additional analytics and monitoring features
- Integrate with external billing systems
- Support for custom model endpoints
- Extend dashboard with new visualization components

## 📚 Documentation

### Project Documentation
- `project_analysis.md` - Requirements and analysis
- `system_design.md` - Architecture and design
- `api_endpoints.md` - API specifications
- `production_deployment_guide.md` - Deployment instructions

### Code Documentation
- All API endpoints include Swagger documentation
- Inline code comments for complex logic
- Configuration file documentation

## 🚀 Production Deployment

### Automated Deployment
```bash
# Run automated deployment script
./deploy.sh

# Verify deployment
python test_production_deployment.py
```

### Manual Deployment
1. Configure environment variables in `.env`
2. Run database migrations: `python database_migration.py migrate`
3. Start services: `docker-compose up -d`
4. Verify health: `curl http://localhost:8000/health`

### Monitoring Setup
- Prometheus metrics available at `/metrics`
- Grafana dashboards for visualization
- Health checks for all services

## 📝 Support

For issues and questions:
1. Check the API documentation at `http://localhost:8000/docs`
2. Review the project documentation files
3. Run test suites to verify functionality
4. Check service logs for debugging

## 🎯 Project Status

**✅ Complete Features:**
- Core API Gateway functionality
- User and model management
- Usage tracking and analytics
- Rate limiting and budget controls
- Web dashboard interface
- Production deployment configuration
- Comprehensive test suites

**📊 Production Ready:**
- Security implementations
- Error handling and validation
- Performance optimizations
- Monitoring and health checks
- Documentation and guides

This project provides a complete, production-ready API gateway solution for managing multiple LLM providers with comprehensive monitoring and control capabilities.

