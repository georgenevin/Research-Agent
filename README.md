# Research Agent

An intelligent AI-powered research agent that conducts web research, summarizes findings, and iteratively refines results based on supervisor feedback. Built with LangChain, LangGraph, and powered by Azure OpenAI.

## Overview

The Research Agent is a multi-agent system that automates the research process through a collaborative workflow:

1. **Research Agent** - Conducts web searches using Tavily API and scrapes relevant web pages
2. **Summarizer Agent** - Creates concise summaries of research findings
3. **Supervisor Agent** - Reviews results and provides feedback for refinement

The system iteratively improves research quality through multiple review cycles (max 3 revisions) until the supervisor approves the final summary.

## Features

- 🔍 **Intelligent Web Research** - Uses Tavily API for comprehensive web searches
- 🌐 **Web Scraping** - Extracts and processes content from multiple web pages
- 📝 **Automated Summarization** - Generates concise, accurate summaries
- 👁️ **Iterative Refinement** - Multi-cycle review process with supervisor feedback
- 🔗 **LLM Integration** - Powered by Azure OpenAI GPT models
- ⚡ **Async Support** - Fully asynchronous implementation for high performance
- 🔐 **State Management** - Persistent state tracking across research cycles

## Architecture

The agent uses a state graph architecture with three main nodes:

```
START → Supervisor Agent → Research Agent ↗
           ↓                              ↓
      Summarizer Agent ←───────────────┘
           ↓
        (Feedback Loop)
           ↓
        END
```

### State Management

The `ResearchAgentState` TypedDict tracks:
- `query` - The user's research query
- `research_results` - Web search and scraping results
- `research_feedback` - Supervisor feedback for the researcher
- `summary` - Generated summary of findings
- `summary_approved` - Whether summary meets quality standards
- `revision_notes` - Feedback for summary refinement
- `revision_counter` - Number of revision cycles (max 3)

## Setup

### Prerequisites

- Python 3.13+
- Azure OpenAI API credentials
- Tavily API key
- PostgreSQL (optional, for state persistence)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/georgenevin/Research-Agent.git
cd Research-Agent
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root:
```env
OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
OPENAI_API_KEY=your_azure_openai_api_key
TAVILY_URL=http://localhost:8000  # MCP Tavily server endpoint
```

## Usage

Run the research agent from the command line:

```bash
python main.py
```

Enter your research topic when prompted:
```
What is your research topic? What are the latest developments in quantum computing?
```

The agent will:
1. Conduct initial research using Tavily
2. Scrape up to 3 relevant web pages
3. Generate a summary
4. Have the supervisor review the findings
5. Iteratively refine until approved (or max revisions reached)
6. Output the final research results

## Dependencies

Key dependencies include:

- **LangChain** - LLM framework and agent orchestration
- **LangGraph** - Workflow/graph management for multi-agent systems
- **Azure Identity** - Azure authentication
- **LangChain OpenAI** - Azure OpenAI integration
- **LangChain Tavily** - Web search integration
- **BeautifulSoup4** - HTML parsing and web scraping
- **FastAPI + Uvicorn** - API server framework
- **PostgreSQL** - Optional state persistence

## Configuration

### Tool Limits

The research agent enforces the following tool call limits:
- `tavily_research`: Maximum 1 call
- `web_scraper`: Maximum 3 calls per research cycle

These limits ensure efficient research without excessive API calls.

### Revision Cycles

The system will run up to 3 revision cycles:
1. Initial research and summary
2. First revision based on feedback
3. Second revision based on feedback
4. Third revision (final attempt)

After 3 revisions, the current summary is automatically approved regardless of supervisor feedback.

## Architecture Components

### Research Agent
- Calls Tavily API for web searches
- Selects up to 3 URLs from results
- Scrapes content from selected URLs
- Returns consolidated research findings

### Summarizer Agent
- Receives research findings
- Incorporates supervisor feedback if available
- Generates clear, concise summaries

### Supervisor Agent
- Reviews research quality and summary completeness
- Provides structured feedback
- Makes decisions: `NEED_RESEARCH`, `NEED_SUMMARY`, or `APPROVED`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Future Enhancements

- [ ] Multi-query support
- [ ] Source citation tracking
- [ ] Custom research parameters
- [ ] Web UI interface
- [ ] Advanced filtering options
- [ ] Export to multiple formats (PDF, Markdown)

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
