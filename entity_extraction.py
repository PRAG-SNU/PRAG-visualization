import os
import json
import csv
import time
import fitz  # PyMuPDF
import openai

# Set your OpenAI API key here
# Example: openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = "YOUR_OPENAI_API_KEY"

# Folder containing the PDF files to process
# Example: folder_path = "/path/to/your/papers"
folder_path = "/path/to/your/papers"

# Define output file names or paths
chunk_file_path = "chunks.json"
checkpoint_file = "checkpoint.txt"
output_csv = "output.csv"
output_json = "output.json"

class PDFParser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def extract_text(self):
        """
        Extracts text from the PDF file using PyMuPDF (fitz).
        """
        try:
            doc = fitz.open(self.pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            print(f"Failed to extract text from {self.pdf_path}: {e}")
            return ""

    def extract_abstract_or_full_text(self):
        """
        Attempts to extract only the 'Abstract' section. If not found, 
        returns the full text.
        """
        text = self.extract_text()

        # Search for Abstract keywords
        abstract_start_keywords = ["Abstract", "ABSTRACT", "A B S T R A C T"]
        abstract_text = None

        for keyword in abstract_start_keywords:
            if keyword in text:
                start_index = text.find(keyword) + len(keyword)
                abstract_text = text[start_index:].strip()
                break

        # If Abstract is not found, use full text
        if abstract_text:
            return abstract_text
        else:
            print("[INFO] Abstract not found, using full text instead.")
            return text

def chunk_text(text, chunk_size=1500):
    """
    Splits the text into chunks of words. Each chunk contains up to `chunk_size` words.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(' '.join(words[i:i + chunk_size]))
    return chunks

def save_chunks_to_file(chunks, file_path):
    """
    Saves the list of text chunks to a JSON file.
    """
    with open(file_path, 'w') as f:
        json.dump(chunks, f)

def load_chunks_from_file(file_path):
    """
    Loads text chunks from a JSON file if it exists.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return None

def save_checkpoint(filename, chunk_index):
    """
    Saves checkpoint data (current file name and chunk index) to resume processing.
    """
    with open(checkpoint_file, 'w') as f:
        f.write(f"{filename},{chunk_index}")

def load_checkpoint():
    """
    Loads checkpoint data from the file to determine the last processed chunk index.
    """
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            data = f.read().strip()
            if data:
                filename, chunk_index = data.split(',')
                return filename, int(chunk_index)
    return None, 0

def classify_spatial(label, spatial_scale):
    """
    Determines the spatial classification of an entity 
    based on predefined keywords in `spatial_scale`.
    """
    if label is None:
        return "Unknown"
    
    for scale, keywords in spatial_scale.items():
        if any(keyword in label for keyword in keywords):
            return scale
    return "Unknown"

def classify_temporal(label, temporal_scale):
    """
    Determines the temporal classification of an entity 
    based on predefined keywords in `temporal_scale`.
    """
    if label is None:
        return "Unknown"
    
    for scale, keywords in temporal_scale.items():
        if any(keyword in label for keyword in keywords):
            return scale
    return "Unknown"

def append_to_csv(data, filename, spatial_scale, temporal_scale):
    """
    Appends extracted entities and relationships to a CSV file.
    Each entity is classified according to spatial and temporal scales.
    """
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["Entity/Relationship", "Label/Type", "Spatial Scale", "Temporal Scale", "Properties/From", "To"])
        
        for entity in data.get("entities", []):
            if entity.get("type") not in ["publication", "organization"]:
                spatial_label = classify_spatial(entity.get("label"), spatial_scale)
                temporal_label = classify_temporal(entity.get("label"), temporal_scale)
                writer.writerow([
                    "Entity",
                    entity.get("label"),
                    spatial_label,
                    temporal_label,
                    json.dumps(entity.get("properties"), ensure_ascii=False),
                    ""
                ])

        for relationship in data.get("relationships", []):
            writer.writerow([
                "Relationship",
                relationship.get("type"),
                "",
                "",
                json.dumps(relationship.get("from"), ensure_ascii=False),
                json.dumps(relationship.get("to"), ensure_ascii=False)
            ])

def append_to_json(data, filename):
    """
    Appends extracted entities and relationships to a JSON file.
    If the file does not exist, creates one.
    """
    if os.path.exists(filename):
        with open(filename, 'r+', encoding='utf-8') as file:
            existing_data = json.load(file)
            existing_data["entities"].extend(
                [entity for entity in data.get("entities", []) if entity.get("type") not in ["publication", "organization"]]
            )
            existing_data["relationships"].extend(data.get("relationships", []))
            file.seek(0)
            json.dump(existing_data, file, ensure_ascii=False, indent=4)
    else:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump({
                "entities": [
                    entity for entity in data.get("entities", []) if entity.get("type") not in ["publication", "organization"]
                ],
                "relationships": data.get("relationships", [])
            }, file, ensure_ascii=False, indent=4)

def extract_entities_and_relationships(text):
    """
    Uses the OpenAI ChatCompletion API to extract entities and relationships 
    from the provided text, returning the results as a JSON-like dictionary.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Adjust model if needed
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Extract entities and relationships from the following text and format them as JSON:\n{text}"}
            ],
            max_tokens=2048,
            n=1,
            stop=None,
            temperature=0.5
        )

        response_content = response['choices'][0]['message']['content'].strip()

        if not response_content:
            print("API returned an empty response.")
            return {"entities": [], "relationships": []}

        # If the response is enclosed in triple backticks or similar, remove them
        if response_content.startswith("```json"):
            response_content = response_content.lstrip("```json").rstrip("```").strip()

        return json.loads(response_content)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON from API response: {e}")
        return {"entities": [], "relationships": []}
    except Exception as e:
        print(f"API request failed: {e}")
        return {"entities": [], "relationships": []}

def process_pdfs(pdf_paths):
    """
    Main function to process the list of PDF files. Extracts text from each file,
    splits it into chunks, and sends each chunk to the OpenAI API for entity 
    and relationship extraction.
    """
    spatial_scale = {
        "Molecular Level": ["Electron Transport Chain", "Photosynthetic Pigments", "RuBisCO", "Enzyme"],
        "Cellular and Tissue Level": ["Chloroplast", "Cytoplasmic", "Mesophyll", "Guard Cells"],
        "Leaf and Canopy Level": ["Leaf Surface", "Internal Structure", "Vertical Structure", "Horizontal Structure"],
        "Crop Arrangement": ["Crop", "Irrigation", "Water Stress"],
        "Microenvironment Level": ["Microclimate", "Soil Composition"],
        "Macroenvironment Level": ["Climate Change", "Atmospheric Composition"]
    }

    temporal_scale = {
        "Immediate Response": ["Light Saturation", "Photoprotection", "Instantaneous"],
        "Short-Term Response": ["Stomatal Opening", "Gene Expression", "Diurnal Changes"],
        "Medium-Term Response": ["Chlorophyll Content", "Circadian Rhythm"],
        "Medium to Long-Term Response": ["Photosynthetic Machinery", "Acclimation", "Seasonal Changes"],
        "Long-Term Response": ["Evolutionary Adaptation", "Community Adaptation"],
        "Very Long-Term Response": ["Ecosystem Changes", "Evolutionary Replacement"]
    }

    for pdf_path in pdf_paths:
        pdf_parser = PDFParser(pdf_path)
        text = pdf_parser.extract_abstract_or_full_text()

        if not text:
            print(f"No text found in {pdf_path}, skipping this file.")
            continue

        # Attempt to load existing chunks from file
        chunks = load_chunks_from_file(chunk_file_path)
        if chunks is None:
            # If no chunks file found, create new chunks
            chunks = chunk_text(text)
            save_chunks_to_file(chunks, chunk_file_path)

        last_filename, last_chunk_index = load_checkpoint()
        start_index = last_chunk_index if last_filename == pdf_path else 0

        # Process each chunk and extract entities and relationships
        for i in range(start_index, len(chunks)):
            entities_and_relationships = extract_entities_and_relationships(chunks[i])

            # Append extracted data to CSV and JSON
            append_to_csv(entities_and_relationships, output_csv, spatial_scale, temporal_scale)
            append_to_json(entities_and_relationships, output_json)

            # Update checkpoint
            save_checkpoint(pdf_path, i)
            time.sleep(1)

        # Remove temporary chunk and checkpoint files after processing each PDF
        if os.path.exists(chunk_file_path):
            os.remove(chunk_file_path)
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)

if __name__ == "__main__":
    # Gather PDF files from the specified folder
    pdf_paths = [
        os.path.join(folder_path, f) 
        for f in os.listdir(folder_path) 
        if f.endswith('.pdf')
    ]
    process_pdfs(pdf_paths)
