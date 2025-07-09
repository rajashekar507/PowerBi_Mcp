# 🤖 AI Power BI Dashboard Generator

A production-ready system that creates **real Power BI dashboards** using AI. Upload your data, describe what you want, and get a fully functional Power BI dashboard with real integrations.

## ⚡ Key Features

- **Real AI Integration**: Uses OpenAI GPT-4 or Anthropic Claude for intelligent analysis
- **Real Power BI Integration**: Creates actual Power BI workspaces, datasets, and dashboards
- **Smart Data Processing**: Handles Excel, CSV, JSON files with intelligent schema detection
- **Professional UI**: Modern React frontend with real-time progress tracking
- **Production Ready**: No simulation code - everything works with real services

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- Node.js 16+
- Power BI Pro account
- Azure App Registration (for Power BI API)
- OpenAI or Anthropic API key

### 2. Installation

```bash
# Clone and setup
git clone <your-repo>
cd PowerBI_V2

# Run automated setup
python setup_script.py

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install
```

### 3. Configuration

**CRITICAL**: Configure your `.env` file with real credentials:

```env
# AI API Keys (REQUIRED - Add at least one)
OPENAI_API_KEY=sk-your-real-openai-key
ANTHROPIC_API_KEY=your-real-anthropic-key

# Power BI Configuration (REQUIRED)
POWER_BI_TENANT_ID=your-azure-tenant-id
POWER_BI_CLIENT_ID=your-azure-app-client-id
POWER_BI_CLIENT_SECRET=your-azure-app-client-secret
POWER_BI_USERNAME=your-powerbi-username
POWER_BI_PASSWORD=your-powerbi-password
```

### 4. Azure App Registration Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to "App registrations" → "New registration"
3. Name: "PowerBI Dashboard Generator"
4. Redirect URI: `http://localhost:8000/auth/callback`
5. After creation, note down:
   - Application (client) ID
   - Directory (tenant) ID
6. Go to "Certificates & secrets" → Create new client secret
7. Go to "API permissions" → Add Power BI Service permissions:
   - `Dataset.ReadWrite.All`
   - `Dashboard.ReadWrite.All`
   - `Report.ReadWrite.All`
   - `Workspace.ReadWrite.All`

### 5. Run the System

```bash
# Start both backend and frontend
python run_script.py

# Or manually:
# Backend: python main.py
# Frontend: cd frontend && npm start
```

## 📊 How It Works

### Real Data Flow

1. **Upload**: User uploads Excel/CSV/JSON files
2. **AI Analysis**: GPT-4/Claude analyzes data structure and user requirements
3. **Power BI Creation**: System creates real Power BI workspace and dataset
4. **Dashboard Generation**: AI generates DAX formulas and visualization configs
5. **Real Output**: User gets actual Power BI dashboard URL and .pbix download

### No Simulation Code

- ❌ No dummy data generation
- ❌ No fallback responses
- ❌ No simulation modes
- ✅ Real AI API calls only
- ✅ Real Power BI API integration
- ✅ Real dashboard creation

## 🔧 API Endpoints

### Core Endpoints

- `POST /upload` - Upload data files
- `POST /chat` - Chat with AI assistant
- `POST /create-dashboard` - Create real Power BI dashboard
- `GET /job-status/{job_id}` - Track dashboard creation progress
- `GET /conversations` - List chat conversations

### Real Integration Points

- **OpenAI GPT-4**: Dashboard analysis and DAX generation
- **Anthropic Claude**: Alternative AI provider
- **Power BI REST API**: Workspace, dataset, and dashboard creation
- **Azure AD**: Authentication for Power BI access

## 🛠️ Architecture

```
Frontend (React) → FastAPI Backend → AI Services (OpenAI/Anthropic)
                                  → Power BI REST API
                                  → Data Processing Pipeline
```

### Core Components

- **`main_server.py`**: FastAPI application with real API endpoints
- **`ai_client.py`**: Real AI integration (no fallbacks)
- **`powerbi_client.py`**: Real Power BI API client
- **`data_processor.py`**: Smart data analysis and processing
- **`langchain_controller.py`**: Advanced AI workflow orchestration

## 🔒 Security & Production

### Environment Variables

All sensitive data is stored in environment variables:
- API keys are never hardcoded
- Power BI credentials are encrypted in transit
- Database connections use secure protocols

### Error Handling

- Real error messages from AI services
- Power BI API error propagation
- Comprehensive logging for debugging
- No fallback to dummy data

## 📈 Monitoring & Logging

```python
# Logs are written to app.log
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=app.log
```

Monitor real-time:
- AI API usage and costs
- Power BI API rate limits
- Dashboard creation success rates
- User interaction patterns

## 🚨 Troubleshooting

### Common Issues

1. **"No AI API keys configured"**
   - Add real OpenAI or Anthropic key to `.env`
   - System will not start without AI integration

2. **"Power BI authentication failed"**
   - Verify Azure app registration
   - Check tenant ID, client ID, and secret
   - Ensure Power BI API permissions are granted

3. **"Dashboard creation failed"**
   - Check Power BI Pro license
   - Verify workspace creation permissions
   - Review API rate limits

### Debug Mode

```bash
# Enable debug logging
DEBUG=True
LOG_LEVEL=DEBUG

# Run with verbose output
python main.py
```

## 📝 Development

### Adding New Features

1. **New AI Providers**: Extend `ai_client.py`
2. **New Data Sources**: Extend `data_processor.py`
3. **New Visualizations**: Update Power BI templates
4. **New UI Components**: Add to React frontend

### Testing

```bash
# Run backend tests
pytest

# Test AI integration
python -c "from ai_client import AIClient; print('AI client works!')"

# Test Power BI connection
python -c "from powerbi_client import PowerBIClient; print('Power BI client works!')"
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add real integration tests
4. Submit pull request

**Note**: All contributions must maintain the "no simulation" principle.

## 📄 License

MIT License - See LICENSE file for details.

## 🆘 Support

For issues with:
- **AI Integration**: Check API key validity and quotas
- **Power BI Integration**: Verify Azure app permissions
- **Data Processing**: Check file formats and data quality
- **Frontend Issues**: Check React console for errors

---

**⚠️ IMPORTANT**: This system requires real API keys and credentials. It will not function in simulation mode. All features are designed for production use with actual services.