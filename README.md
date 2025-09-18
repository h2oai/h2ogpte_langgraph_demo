# h2oGPTe x LangGraph Demo

## Getting Started

1. Install [uv](https://docs.astral.sh/uv/#installation)
2. Run `uv sync` to install all dependencies
3. Set up h2oGPTe API key (see [h2oGPTe Setup](#h2ogpte-setup) below)
4. Set up your LANGSMITH API key (see [LangSmith Setup](#langsmith-setup) below) (optional)
5. Run the app `uv run langgraph dev`
6. Input

```text
Borrower Id: TechManufacture Inc
Sector: Advanced Manufacturing
```

## h2oGPTe Setup

This application requires an h2oGPTe API key to function. Follow these steps to configure it:

### 1. Get Your h2oGPTe API Key

- Generate or retrieve your API key from h2oGPTe

### 2. Configure h2oGPTe Env Variables

Create a `.env` file in the project root directory:

```bash
# Copy the example file
cp .env.example .env

# Edit the .env file and add your API key
H2OGPTE_API_KEY=your_actual_api_key_here
```

### 3. Set your h2oGPTe instance

The demo defaults to h2oGPTe freemium version. If you wish to change environments, update the `.env`

```bash
# Edit the .env file to change h2oGPTe instance
H2OGPTE_URL=your_h2ogpte_instance

# Run the collection creation script
python3 create_collections.py
```

## LangSmith Setup

LangSmith provides powerful tracing, debugging, and monitoring capabilities for your LangGraph workflows. While optional, it's highly recommended for development and production use.

### 1. Get Your LangSmith API Key

1. Sign up for a free account at [smith.langchain.com](https://smith.langchain.com/)
2. Navigate to your account settings
3. Generate an API key

### 2. Configure LangSmith Env Variables

Add your LangSmith API key to your `.env` file:

```bash
# .env
LANGSMITH_API_KEY=lsv2_pt_...
```

### 3. Benefits of LangSmith Integration

- **Tracing**: Visualize the execution flow of your workflows
- **Debugging**: Step through each node and inspect state changes
- **Monitoring**: Track performance metrics and identify bottlenecks
- **Collaboration**: Share traces with team members for debugging
- **Analytics**: Analyze usage patterns and optimize your workflows

## Developer Guide

Ensure `uv` is [installed](https://docs.astral.sh/uv/getting-started/installation/) to inherit all other tools.

```bash
# Install dependencies
uv sync --dev
```
