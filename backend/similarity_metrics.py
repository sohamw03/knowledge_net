import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import csv # For CSV output
import os # To get filename for report

# --- 1. Load Data --- (No changes from previous version)
def load_data(filepath="output.log.json"):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filepath}'.")
        return None

# --- 2. Text Extraction --- (No changes from previous version)
def extract_main_content(data):
    return data.get("content", "")

def extract_source_texts_from_tree(current_node):
    sources_list = []
    if isinstance(current_node, dict):
        if "sources" in current_node and isinstance(current_node["sources"], dict):
            for url, raw_content in current_node["sources"].items():
                if isinstance(raw_content, str) and raw_content.strip():
                    sources_list.append({"id": url, "text": raw_content})
        for key, value in current_node.items():
            if key != "sources":
                sources_list.extend(extract_source_texts_from_tree(value))
    elif isinstance(current_node, list):
        for item in current_node:
            sources_list.extend(extract_source_texts_from_tree(item))
    return sources_list

# --- 3. Text Preprocessing --- (No changes from previous version)
def preprocess_text(text):
    if not text or not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'\W+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- 4. Similarity Calculation ---
# Modified to return both similarity_scores and the count of valid_source_info_for_results
def calculate_similarity(main_text, source_texts_list):
    if not main_text.strip():
        # print("Main report content is empty. Cannot calculate similarity.") # Will be handled by caller
        return {}, 0
    if not source_texts_list:
        # print("No source texts extracted. Cannot calculate similarity.") # Will be handled by caller
        return {}, 0

    preprocessed_main_text = preprocess_text(main_text)
    
    all_texts_for_tfidf = [preprocessed_main_text]
    valid_source_info_for_results = []

    for source_info in source_texts_list:
        source_text = source_info.get("text", "")
        preprocessed_s_text = preprocess_text(source_text)
        if preprocessed_s_text:
            all_texts_for_tfidf.append(preprocessed_s_text)
            valid_source_info_for_results.append(source_info)
        # else:
            # print(f"Info: Source '{source_info.get('id', 'unknown')}' resulted in empty text after preprocessing, skipping.")

    if len(all_texts_for_tfidf) < 2:
        # print("Not enough text content (main text + at least one valid source after preprocessing) to compare.")
        return {}, len(valid_source_info_for_results)

    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_texts_for_tfidf)
    except ValueError as e:
        print(f"Error during TF-IDF vectorization: {e}.")
        return {}, len(valid_source_info_for_results)

    main_text_vector = tfidf_matrix[0]
    source_vectors = tfidf_matrix[1:]

    if source_vectors.shape[0] == 0:
        return {}, len(valid_source_info_for_results)

    similarities = cosine_similarity(main_text_vector, source_vectors)
    
    results = {}
    for i, source_info in enumerate(valid_source_info_for_results):
        results[source_info["id"]] = similarities[0, i]
        
    return results, len(valid_source_info_for_results)

# --- 5. Aggregate Metrics Calculation --- (New Function)
def calculate_aggregate_metrics(similarity_scores, total_sources_extracted_from_tree, sources_used_in_similarity_calc):
    """Calculates aggregate metrics from individual similarity scores."""
    metrics = {
        "total_sources_in_tree": total_sources_extracted_from_tree,
        "sources_used_for_sim": sources_used_in_similarity_calc,
        "average_similarity": 0.0,
        "max_similarity": 0.0,
        "top_source_url": "N/A",
        "highly_similar_sources_gt_0_3": 0,
        "highly_similar_sources_gt_0_5": 0
    }

    if not similarity_scores: # No scores to aggregate
        return metrics

    scores = list(similarity_scores.values())
    metrics["average_similarity"] = np.mean(scores) if scores else 0.0
    metrics["max_similarity"] = np.max(scores) if scores else 0.0
    
    if scores:
        for url, score in similarity_scores.items():
            if score == metrics["max_similarity"]:
                metrics["top_source_url"] = url
                break # Take the first one if multiple have max score
                
    metrics["highly_similar_sources_gt_0_3"] = sum(1 for score in scores if score > 0.3)
    metrics["highly_similar_sources_gt_0_5"] = sum(1 for score in scores if score > 0.5)
    
    return metrics

# --- Main Execution ---
if __name__ == "__main__":
    # --- IMPORTANT: Update this list with paths to your JSON files ---
    sample_files = [
        "output.log.json", 
        # "output_sample2.log.json", # Example: add more files
        # "output_sample3.log.json"
    ]
    # You can also use glob to find all *.json files in a directory if needed:
    # import glob
    # sample_files = glob.glob("path/to/your/json_files/*.json")

    if not sample_files or not os.path.exists(sample_files[0]): # Basic check
        print("Please update the 'sample_files' list with valid paths to your JSON files.")
        print(f"Currently looking for: {sample_files}")
        exit()
        
    all_samples_aggregated_metrics = []

    print("Processing multiple sample files...\n")

    for filepath in sample_files:
        print(f"--- Processing file: {filepath} ---")
        data = load_data(filepath)

        if not data:
            print(f"Skipping file {filepath} due to loading error.\n")
            # Add a placeholder entry or skip
            all_samples_aggregated_metrics.append({
                "sample_file": os.path.basename(filepath), 
                "error": "Failed to load or parse JSON"
            })
            continue

        main_report_content = extract_main_content(data)
        research_tree_data = data.get("research_tree")

        if not main_report_content:
            print("Could not extract main report content.")
            all_samples_aggregated_metrics.append({
                "sample_file": os.path.basename(filepath), 
                "error": "No main content"
            })
            continue # Or add more default values
            
        if research_tree_data is None:
            print("Could not find 'research_tree' in the data or it is null.")
            all_samples_aggregated_metrics.append({
                "sample_file": os.path.basename(filepath),
                 "total_sources_in_tree": 0, "sources_used_for_sim":0,
                "error": "No research tree"
            })
            continue # Or add more default values

        source_texts_from_tree = extract_source_texts_from_tree(research_tree_data)
        total_extracted_count = len(source_texts_from_tree)
        print(f"Extracted {total_extracted_count} source entries from the tree.")

        if not source_texts_from_tree:
            print("No source texts could be extracted from the research_tree.")
            agg_metrics = calculate_aggregate_metrics({}, total_extracted_count, 0)
        else:
            similarity_scores, num_sources_used_in_calc = calculate_similarity(main_report_content, source_texts_from_tree)
            if similarity_scores:
                print(f"Calculated similarities for {len(similarity_scores)} sources (out of {num_sources_used_in_calc} with text).")
            else:
                print(f"Could not calculate similarity scores (used {num_sources_used_in_calc} sources with text).")
            agg_metrics = calculate_aggregate_metrics(similarity_scores, total_extracted_count, num_sources_used_in_calc)
        
        agg_metrics["sample_file"] = os.path.basename(filepath) # Add filename to the metrics
        all_samples_aggregated_metrics.append(agg_metrics)
        print(f"Aggregated metrics for {filepath}: {agg_metrics}\n")

    # --- Outputting the Combined Metrics ---
    if not all_samples_aggregated_metrics:
        print("No data processed to generate a report.")
    else:
        print("\n--- Combined Metrics Table ---")
        
        # Define header based on keys from the first valid entry (if any)
        # Fallback headers if all entries had errors
        header = ["sample_file", "total_sources_in_tree", "sources_used_for_sim", 
                  "average_similarity", "max_similarity", "top_source_url",
                  "highly_similar_sources_gt_0_3", "highly_similar_sources_gt_0_5", "error"]
        
        # Try to get header from a successful processing attempt
        first_successful_metric = next((m for m in all_samples_aggregated_metrics if "error" not in m), None)
        if first_successful_metric:
            header = list(first_successful_metric.keys())


        # Print to console
        # Dynamically create format string for cleaner table printing
        col_widths = {h: len(h) for h in header}
        for row_metrics in all_samples_aggregated_metrics:
            for h in header:
                col_widths[h] = max(col_widths[h], len(str(row_metrics.get(h, ""))))
        
        header_fmt = " | ".join([f"{{:<{col_widths[h]}}}" for h in header])
        row_fmt = " | ".join([f"{{:<{col_widths[h]}}}" for h in header])

        print(header_fmt.format(*header))
        print("-+-".join(['-' * col_widths[h] for h in header])) # Separator line

        for sample_metrics in all_samples_aggregated_metrics:
            # Ensure all keys are present for formatting, defaulting to "N/A" or empty
            row_values = [sample_metrics.get(h, "N/A") for h in header] 
            # Format floats
            for i, h_key in enumerate(header):
                if isinstance(row_values[i], float):
                    row_values[i] = f"{row_values[i]:.4f}"
            print(row_fmt.format(*row_values))

        # Write to CSV
        csv_filename = "similarity_metrics_report.csv"
        try:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=header)
                writer.writeheader()
                reader = csv.DictReader(csvfile, fieldnames=header)
                old_rows = list(reader)
                writer.writerows(old_rows)
                for sample_metrics in all_samples_aggregated_metrics:
                    # Create a full dict for DictWriter, ensuring all header fields are present
                    row_to_write = {h: sample_metrics.get(h, "N/A") for h in header}
                    writer.writerow(row_to_write)
            print(f"\nMetrics report saved to: {csv_filename}")
        except IOError:
            print(f"\nError: Could not write metrics report to {csv_filename}")
