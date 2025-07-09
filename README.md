# 🤖 AI Power BI Dashboard Generator

A ChatGPT/Claude-style interface for creating professional Power BI dashboards through natural language conversations. Upload your data, chat with AI, and get real Power BI dashboards instantly!

## ✨ Features

- **🎨 ChatGPT/Claude Interface**: Modern black & red Netflix-style design
- **🤖 AI-Powered**: GPT-4 and Claude integration for intelligent dashboard creation
- **📊 Real Power BI Integration**: Creates actual Power BI workspaces and dashboards
- **📁 Multi-Format Support**: Excel, CSV, JSON, and image uploads
- **💬 Natural Language**: Just describe what you want - "Create a sales dashboard with monthly trends"
- **🔄 Real-time Progress**: Track dashboard creation status
- **💾 Conversation History**: Save and resume conversations
- **🔗 Direct Links**: Get direct links to view and download dashboards

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 14+
- Power BI Pro account
- OpenAI API key
- Anthropic API key (optional)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/rajashekar507/PowerBi_Mcp.git
cd PowerBi_Mcp
```

2. **Set up Python environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

3. **Set up Frontend**
```bash
cd frontend
npm install
cd ..
```

4. **Configure Environment**
Create a `.env` file in the root directory:
```env
# AI API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Power BI Configuration
POWERBI_CLIENT_ID=your_powerbi_client_id
POWERBI_CLIENT_SECRET=your_powerbi_client_secret
POWERBI_TENANT_ID=your_tenant_id
POWERBI_USERNAME=your_powerbi_username
POWERBI_PASSWORD=your_powerbi_password

# Database
DATABASE_URL=sqlite:///conversations.db

# Server Configuration
HOST=127.0.0.1
PORT=8001
DEBUG=True

# Security
SECRET_KEY=your_secret_key_here
```

### Running the Application

1. **Start the Backend**
```bash
python main.py
```

2. **Start the Frontend** (in a new terminal)
```bash
cd frontend
npm start
```

3. **Access the Application**
- Frontend: http://localhost:3000
- API Documentation: http://127.0.0.1:8001/docs

## 📋 Usage Workflow

1. **Access**: Open http://localhost:3000
2. **Upload Data**: Drag & drop Excel/CSV/JSON files
3. **Chat**: Type natural language requests like:
   - "Create a sales dashboard with monthly trends"
   - "Build an executive summary with KPIs"
   - "Make a financial report with charts"
4. **Get Dashboard**: Receive real Power BI dashboard links
5. **Download**: Get .pbix files for offline use

## 🏗️ Architecture

```
User Access (http://localhost:3000) 
     ↓
  React Frontend (ChatGPT/Claude Style)
     ↓
  Backend API (/upload, /chat)
     ↓
  Data Processor (analyzes files)
     ↓
  AI Client (GPT-4/Claude)
     ↓
  LangChain Controller
     ↓
  Power BI Client (creates dashboards)
     ↓
  Memory Manager (saves conversations)
     ↓
  Dashboard URLs returned
```

## 📁 Project Structure

```
PowerBi_Mcp/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (create this)
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── src/                  # Backend source code
│   ├── api/             # FastAPI endpoints
│   ├── core/            # Core business logic
│   ├── database/        # Database management
│   └── utils/           # Utility functions
├── frontend/            # React frontend
│   ├── src/            # React source code
│   ├── public/         # Static files
│   └── package.json    # Node dependencies
├── config/             # Configuration files
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── uploads/            # File uploads (auto-created)
├── output/             # Generated files (auto-created)
├── logs/               # Application logs (auto-created)
└── data/               # Data storage (auto-created)
```

## 🔧 Configuration

### Power BI Setup
1. Register an app in Azure AD
2. Get Client ID, Client Secret, and Tenant ID
3. Enable Power BI API permissions
4. Add credentials to `.env` file

### AI API Setup
1. Get OpenAI API key from https://platform.openai.com/
2. Get Anthropic API key from https://console.anthropic.com/
3. Add keys to `.env` file

## 🎨 Interface Features

- **Netflix-Style Design**: Black background with red accents
- **ChatGPT Layout**: Full-width messages with avatars
- **Responsive Design**: Works on desktop and mobile
- **File Upload**: Drag & drop or click to upload
- **Real-time Chat**: Instant AI responses
- **Progress Tracking**: Visual progress indicators
- **Conversation History**: Sidebar with saved chats

## 🔌 API Endpoints

- `POST /api/upload` - Upload data files
- `POST /api/chat` - Send chat messages
- `GET /api/conversations` - Get conversation history
- `DELETE /api/conversations/{id}` - Delete conversation
- `GET /api/health` - Health check

## 🛠️ Development

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn src.api.main_server:app --reload --host 127.0.0.1 --port 8001
```

### Frontend Development
```bash
cd frontend
npm start
```

## 🚀 Deployment

### Local Production
```bash
# Build frontend
cd frontend
npm run build

# Run backend
python main.py
```

### Docker (Optional)
```bash
docker-compose up --build
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the documentation
2. Review API docs at http://127.0.0.1:8001/docs
3. Create an issue on GitHub

## 🔄 Updates

- **v2.0**: ChatGPT/Claude interface with Netflix colors
- **v1.0**: Initial release with basic functionality

---

**Made with ❤️ for the Power BI community**