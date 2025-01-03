import os
import csv
import PyPDF2
import openai
import json
import time
import re

# Set your OpenAI API key
# Example: openai.api_key = os.getenv("OPENAI_API_KEY") 
openai.api_key = "YOUR_OPENAI_API_KEY"

# Folder path where the PDF files (papers) are stored
# Example: folder_path = "/path/to/your/papers"
folder_path = "/path/to/your/papers"

# Paths to the CSV output file and checkpoint
csv_file_path = "evaluation_results.csv"
checkpoint_path = "checkpoint.json"

# System prompt to provide strict scoring metrics and instructions
system_prompt = """
As a leading researcher in the fields of plant physiology, biochemistry, biology, structural biology, climatology, environmental engineering, and agronomy, all with a focus on photosynthesis, your goal is to use a language model to refine your research ideas and enhance the quality of your scientific projects. To achieve the highest standards of relevance and accuracy in the model's responses, please evaluate each answer with stringent criteria based on the following metrics:

**Scoring Metrics**:
1. **Scientific Depth**: Assess the accuracy and comprehensiveness of the discussion related to the current scientific understanding of photosynthesis. Scores should reflect the degree to which the response integrates detailed, up-to-date knowledge of photosynthesis, including molecular mechanisms, biochemical pathways, and physiological impacts. Rate this on a scale from 0.00 to 10.00, with the ability to assign scores in 0.01-point increments:
   - **9.00-10.00**: Exceptional depth with flawless integration of advanced concepts, demonstrating a thorough understanding and synthesis of complex ideas.
   - **7.00-8.99**: High level of accuracy with minor gaps in depth or complexity.
   - **4.00-6.99**: Moderate understanding with some superficial treatment of concepts or minor inaccuracies.
   - **1.00-3.99**: Significant inaccuracies, oversimplifications, or major gaps in knowledge.
   - **0.00-0.99**: Almost no accurate or relevant scientific information presented.

2. **Domain Coverage**: Evaluate the breadth of the scientific domains covered in the discussion, especially how well the response incorporates various disciplines related to photosynthesis. The response should ideally include a wide range of interconnected fields such as plant physiology, biochemistry, photochemistry, plant architecture, environmental science, agronomy, climatology, and environmental engineering. Score this on a scale from 0.00 to 10.00, with the ability to assign scores in 0.01-point increments:
   - **9.00-10.00**: Comprehensive coverage across multiple relevant domains, demonstrating interdisciplinary integration.
   - **7.00-8.99**: Broad coverage with minor omissions or less integration of certain relevant fields.
   - **4.00-6.99**: Adequate coverage but limited to a few domains, with some important fields either underrepresented or missing.
   - **1.00-3.99**: Narrow focus with minimal or no inclusion of relevant interdisciplinary perspectives.
   - **0.00-0.99**: No relevant domain coverage beyond the most basic aspects.

**Evaluation Guidelines**:
- Focus exclusively on the scholarly depth and domain coverage, regardless of the paper's length or other characteristics.
- A score of 5.00 or above is considered acceptable, with a score of 10.00 representing an exemplary response.
- It is imperative to avoid 0.5-point rounding in the scoring process. Use 0.01-point increments to provide a detailed and precise assessment.

**Feedback Instructions**:
- After scoring each response, provide constructive feedback specifically aimed at addressing areas needing improvement.
- Focus solely on the deficiencies and suggest practical steps for enhancing the scientific depth and domain coverage in future responses.
- Avoid reiterating positive aspects; concentrate on identifying and articulating areas where the response falls short to guide improvements in subsequent interactions.
- Ensure that feedback is precise, actionable, and geared towards elevating the quality, clarity, and depth of future scientific discussions, thereby fostering unbiased and meaningful progress in photosynthesis research.
"""

def split_text_into_chunks(text, max_tokens=4000):
    """
    Splits a given text into multiple chunks to keep each segment within the maximum token limit.
    """
    words = text.split()
    chunks = []
    chunk = []
    chunk_length = 0

    for word in words:
        chunk.append(word)
        # Approximate token count by character length + spaces
        chunk_length += len(word) + 1
        if chunk_length >= max_tokens:
            chunks.append(' '.join(chunk))
            chunk = []
            chunk_length = 0

    if chunk:
        chunks.append(' '.join(chunk))

    return chunks

def analyze_full_paper(text):
    """
    Analyzes the full text of a paper by splitting it into chunks, then calling the OpenAI API
    to evaluate scientific depth and domain coverage for each chunk.
    """
    chunks = split_text_into_chunks(text)
    scientific_depth_total = 0.0
    domain_coverage_total = 0.0
    count = 0

    for chunk in chunks:
        prompt = f"""
        Evaluate the following section of a research paper based on scientific depth and domain coverage:
        \"{chunk}\"
        
        Provide scores for:
        1. Scientific depth (0.00 to 10.00):
        2. Domain coverage (0.00 to 10.00):
        """
        for attempt in range(3):  # Retry up to 3 times if the API call fails
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",  # Change model if needed
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
                output = response['choices'][0]['message']['content'].strip()

                # Use regex to parse the scores from the response
                scientific_depth_score = None
                domain_coverage_score = None

                match_depth = re.search(r"Scientific [Dd]epth[:\s]+(\d+(\.\d{1,2})?)", output)
                match_coverage = re.search(r"Domain [Cc]overage[:\s]+(\d+(\.\d{1,2})?)", output)

                if match_depth:
                    scientific_depth_score = float(match_depth.group(1))
                if match_coverage:
                    domain_coverage_score = float(match_coverage.group(1))

                if scientific_depth_score is not None and domain_coverage_score is not None:
                    scientific_depth_total += scientific_depth_score
                    domain_coverage_total += domain_coverage_score
                    count += 1
                break  # Exit the retry loop if successful
            except openai.error.OpenAIError as e:
                print(f"API error: {e}")
                time.sleep(5)  # Wait 5 seconds before retrying
        else:
            # If we reach here, all 3 attempts have failed
            print(f"Failed to process chunk after 3 attempts: {chunk[:100]}...")

    if count > 0:
        scientific_depth = scientific_depth_total / count
        domain_coverage = domain_coverage_total / count
    else:
        scientific_depth = 0.0
        domain_coverage = 0.0

    return scientific_depth, domain_coverage

def extract_full_text(file_path):
    """
    Extracts the full text from a PDF file using PyPDF2.
    """
    full_text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                full_text += page.extract_text()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return full_text

def save_checkpoint(data, checkpoint_path):
    """
    Saves the checkpoint data (e.g., already processed files) in JSON format.
    """
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_checkpoint(checkpoint_path):
    """
    Loads the checkpoint data from a JSON file, if it exists.
    """
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def evaluate_papers_in_folder(folder_path, csv_file_path, checkpoint_path):
    """
    Iterates over all PDF files in the specified folder, evaluates them,
    and saves results to a CSV file. Uses checkpointing to avoid re-evaluation
    of already processed files.
    """
    results = []
    checkpoint = load_checkpoint(checkpoint_path)
    processed_files = checkpoint.get('processed_files', []) if checkpoint else []

    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf') and filename not in processed_files:
            file_path = os.path.join(folder_path, filename)
            full_text = extract_full_text(file_path)
            if full_text:
                scientific_depth, domain_coverage = analyze_full_paper(full_text)
                result = {
                    'filename': filename,
                    'scientific_depth': scientific_depth,
                    'domain_coverage': domain_coverage
                }
                results.append(result)
                processed_files.append(filename)

                # Save progress to checkpoint
                save_checkpoint({'processed_files': processed_files, 'results': results}, checkpoint_path)

                # Immediately append the result to CSV
                with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['filename', 'scientific_depth', 'domain_coverage']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    if csvfile.tell() == 0:  # Write header if the file is empty
                        writer.writeheader()
                    writer.writerow(result)

if __name__ == "__main__":
    evaluate_papers_in_folder(folder_path, csv_file_path, checkpoint_path)
    print(f"Evaluation results saved to {csv_file_path}")
