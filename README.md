# Medical Text Summarization System

A system that uses LLMs to generate summaries from medical text files.

## Architecture Overview

The system consists of the following components:

1. FastAPI Backend
2. OpenAI Integration
3. File Processing System: Handles multiple text files from specified directories
4. Logging System: Tracks usage, performance, and errors
5. Testing Suite
6. Dockerization

### Key Features

- Process multiple medical text files in batch
- Customizable summaries based on clinical roles
- Highlighting of critical findings
- Source mapping that links summary points to the original text
- Performance monitoring and token tracking
- Feedback collection mechanism

## Setup Instructions

### Prerequisites

- Python
- Docker
- OpenAI API key

### Directory Structure

```
medicalSummarizer/
├── main.py
├── test_main.py
├── requirements.txt
├── Dockerfile
├── api-key.rtf
└── notes/
    ├── note1.txt
    ├── note2.txt
    └── stroke_notes/
        └── note1.txt
        └── note2.txt
```

### Environment Setup

1. Clone the repository:
   ```
   git clone https://github.com/teferrabg/medicalSummarizer.git
   cd medicalSummarizer
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Place your OpenAI API key RTF file in the project root:
   ```
   cp /path/to/your/api-key.rtf .
   ```


### Running the Application

#### Without Docker

```
python main.py
```

The API will be available at http://localhost:8000

#### With Docker

1. Create Directory for logg and feedback storage:
    ```
    mkdir -p logs feedback
    ```
2. Build the Docker image:
   ```
   docker build -t medical-summarizer .
   ```

3. Run the container:
   ```
   docker run -p 8000:8000 -v /path/to/your/notes:/app/notes -v $(pwd)/api-key.rtf:/app/api-key.rtf   -v $(pwd)/logs:/app/logs -v $(pwd)/feedback:/app/feedback medical-summarizer
   ```

### API Documentation

Once the application is running, you can access the UI at:
http://localhost:8000/docs

## API Endpoints

- `GET /health`: Check if the service is running
- `POST /summarize`: Generate summaries from medical text files
- `POST /feedback`: Submit feedback about generated summaries. The feedbacks will be available in feedback/

## Sample Usage

```python
import requests

# Generate summaries for all text files in a directory
response = requests.post(
    "http://localhost:8000/summarize",
    json={
        "directory": "./notes",
        "role": "physician",
        "format": "brief",
        "highlight_critical": True
    }
)

# Process each summary
for summary in response.json():
    print(f"\nFile: {summary['file_name']}")
    print(f"Summary: {summary['summary']}")
    if summary.get('critical_findings'):
        print(f"Critical findings: {summary['critical_findings']}")

# Submit feedback
requests.post(
    "http://localhost:8000/feedback",
    json={
        "summary_id": summary["summary_id"],
        "rating": 5,
        "comments": "Excellent summary, captured all key points"
    }
)
```
