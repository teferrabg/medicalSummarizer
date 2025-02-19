import os
import logging
from typing import Dict, Any, List, Optional
import time
import json
from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from pydantic import BaseModel, Field
import uvicorn
import openai
from datetime import datetime
import glob

# Configure logging
#get working directory
working_dir = os.getcwd()
#create directory if it does not exist
if not os.path.exists(f"{working_dir}/logs"):
    os.makedirs(f"{working_dir}/logs")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{working_dir}/logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Medical Note Summarizer",
              description="API for summarizing medical notes using LLMs (gpt-4o)")

# Load API key from RTF file
try:
    rtf_path = "api-key.rtf"
    with open(rtf_path, "r") as f:
        api_key = f.read().split("\n")[0]
    openai.api_key = api_key
    logger.info("Successfully loaded API key from RTF file")
except Exception as e:
    logger.error(f"Failed to load API key from RTF file: {str(e)}")
    raise

class FileProcessRequest(BaseModel):
    directory: str = Field(..., description="Directory containing the medical notes")
    role: Optional[str] = Field(None, description="Clinical role (e.g., 'physician', 'nurse')")
    format: Optional[str] = Field(None, description="Summary format (e.g., 'brief', 'detailed')")
    highlight_critical: bool = Field(True, description="Whether to highlight critical findings or not")

class FeedbackRequest(BaseModel):
    summary_id: str = Field(..., description="ID of the summary")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comments: Optional[str] = Field(None, description="Feedback comments")

class SummaryResponse(BaseModel):
    summary_id: str
    file_name: str
    summary: str
    metadata: Dict[str, Any]
    critical_findings: Optional[List[str]] = None
    source_mappings: Optional[Dict[str, List[int]]] = None

def read_text_file(file_path: str) -> str:
    #Read content from a text file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise ValueError(f"Failed to read file {file_path}: {str(e)}")

def get_text_files(directory: str) -> List[str]:
    #Get all .txt files from the specified directory
    if not os.path.exists(directory):
        raise ValueError(f"Directory not found: {directory}")
    
    files = glob.glob(os.path.join(directory, "*.txt"))
    if not files:
        raise ValueError(f"No .txt files found in directory: {directory}")
    
    return files

def summarize_text(text: str, role: Optional[str] = None, 
                  format: Optional[str] = None, 
                  highlight_critical: bool = True) -> Dict[str, Any]:
    #Summarize medical text using OpenAI GPT model
    start_time = time.time()
    
    # Customize prompt based on role and format
    system_message = "You are a medical summarization assistant. Provide a concise summary of the following medical text."
    if role:
        system_message += f" Format it for a {role}."
    if format:
        system_message += f" Use a {format} format."
    if highlight_critical:
        system_message += " Identify and list any critical findings separately at the end of the summary."
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": text}
            ],
        )
        
        summary = response.choices[0].message['content'].strip()

        #get critical findings if present
        critical_findings = None
        if highlight_critical and "Critical Findings" in summary:
            parts = summary.split("Critical Findings")
            summary = parts[0].strip()
            critical_findings = [f.strip().strip("**").strip(":") for f in parts[1].strip().split('\n') if f.strip()]

        #create simple source mappings
        source_mappings = create_simple_source_mapping(text, summary)

        #log token usage
        tokens_used = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        logger.info(f"Token usage: {tokens_used}")
        
        processing_time = time.time() - start_time
        
        return {
            "summary_id": f"sum_{int(time.time())}",
            "summary": summary,
            "metadata": {
                "model": "gpt-4o",
                "role": role,
                "format": format,
                "processing_time_sec": processing_time,
                "tokens": tokens_used,
                "timestamp": datetime.now().isoformat()
            },
            "critical_findings": critical_findings,
            "source_mappings": source_mappings
        }
    
    except Exception as e:
        logger.error(f"Error in summarization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summarization error: {str(e)}")

def create_simple_source_mapping(source_text: str, summary: str) -> Dict[str, List[int]]:
    #Create a simple mapping between summary sentences and source paragraphs
    source_paragraphs = [p.strip() for p in source_text.split('\n') if p.strip()]
    summary_sentences = [s.strip() for s in summary.split('.') if s.strip()]
    
    mappings = {}
    for i, sentence in enumerate(summary_sentences):
        key_terms = [word for word in sentence.split() if len(word) > 5][:3]
        matched_paragraphs = []
        
        for j, paragraph in enumerate(source_paragraphs):
            if any(term.lower() in paragraph.lower() for term in key_terms):
                matched_paragraphs.append(j)
        
        if matched_paragraphs:
            mappings[f"sentence_{i}"] = matched_paragraphs
    
    return mappings

@app.get("/health")
def health_check():
    #Health check endpoint
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/summarize", response_model=List[SummaryResponse])
def create_summaries(request: FileProcessRequest):
    #Generate summaries from medical text files in the specified directory
    logger.info(f"Processing text files from directory: {request.directory}")
    
    try:
        # Get all text files from the directory
        files = get_text_files(request.directory)
        summaries = []
        
        for file_path in files:
            # Read and process each file
            text = read_text_file(file_path)
            if len(text) < 10:
                logger.warning(f"File {file_path} too short, skipping")
                continue
                
            result = summarize_text(
                text=text,
                role=request.role,
                format=request.format,
                highlight_critical=request.highlight_critical
            )
            
            # Add filename to result
            result['file_name'] = os.path.basename(file_path)
            summaries.append(result)
            
            logger.info(f"Generated summary for file: {file_path}")
        
        return summaries
    
    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
def submit_feedback(feedback: FeedbackRequest):
    #Store feedback about a generated summary
    logger.info(f"Received feedback for summary {feedback.summary_id}: rating={feedback.rating}")
    
    feedback_data = {
        "summary_id": feedback.summary_id,
        "rating": feedback.rating,
        "comments": feedback.comments,
        "timestamp": datetime.now().isoformat()
    }

    #get working directory
    working_dir = os.getcwd()

    #create directory if it does not exist
    if not os.path.exists(f"{working_dir}/feedback"):
        os.makedirs(f"{working_dir}/feedback")
    feedback_file = f"{working_dir}/feedback/feedback.jsonl"
    with open(feedback_file, "a") as f:
        f.write(json.dumps(feedback_data) + "\n")
    
    return {"status": "feedback received", "feedback_id": f"fb_{int(time.time())}"}

if __name__ == "__main__":
    logger.info("Starting Medical Note Summarizer API")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
