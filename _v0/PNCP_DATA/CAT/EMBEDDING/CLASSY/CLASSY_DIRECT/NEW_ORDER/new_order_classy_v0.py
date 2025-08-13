import os
import re
import pandas as pd
from tqdm import tqdm

# Define paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
CLASS_PATH = BASE_PATH + "CLASSY\\"
INPUT_PATH = CLASS_PATH + "OUTPUT\\"
OUTPUT_FILE = CLASS_PATH + "UNIFIED_OUTPUT.xlsx"

# For very large datasets, use CSV as intermediate format
TEMP_CSV = CLASS_PATH + "temp_unified_output.csv"

def extract_code(text):
    if pd.isna(text) or text == "":
        return ""
    
    match = re.search(r'([MS]\d{11,15})', text)
    if match:
        return match.group(1)
    return ""

def process_files_with_chunking():
    print("Starting to process files with memory optimization...")
    
    # Get list of all output files
    output_files = [f for f in os.listdir(INPUT_PATH) if f.startswith("OUTPUT_") and f.endswith(".xlsx")]
    output_files.sort()
    
    # Create CSV file for incremental writing
    first_file = True
    total_rows = 0
    
    # Process each file
    for file in tqdm(output_files, desc="Processing files"):
        filepath = os.path.join(INPUT_PATH, file)
        
        try:
            # Read the Excel file
            df = pd.read_excel(filepath, sheet_name="Sheet1")
            
            # Make a new dataframe with just the columns we need
            result_df = pd.DataFrame()
            result_df['id_pncp'] = df['id_pncp']
            
            # Extract codes and swap columns according to the pattern
            swap_pairs = [(1, 10), (2, 9), (3, 8), (4, 7), (5, 6)]
            
            for i, j in swap_pairs:
                # Extract codes and swap TOP columns
                result_df[f'TOP_{i}'] = df[f'TOP_{j}'].apply(extract_code)
                result_df[f'TOP_{j}'] = df[f'TOP_{i}'].apply(extract_code)
                
                # Swap SCORE columns and round to 4 decimal places
                result_df[f'SCORE_{i}'] = df[f'SCORE_{j}'].apply(lambda x: round(x, 4) if pd.notnull(x) else x)
                result_df[f'SCORE_{j}'] = df[f'SCORE_{i}'].apply(lambda x: round(x, 4) if pd.notnull(x) else x)
            
            # Reorder columns to ensure proper ordering
            ordered_columns = ['id_pncp']
            ordered_columns.extend([f'TOP_{i}' for i in range(1, 11)])
            ordered_columns.extend([f'SCORE_{i}' for i in range(1, 11)])
            
            # Reorder the DataFrame columns
            result_df = result_df[ordered_columns]
            
            # Append to CSV file
            result_df.to_csv(TEMP_CSV, mode='w' if first_file else 'a', 
                           header=first_file, index=False, float_format='%.4f')
            
            if first_file:
                first_file = False
            
            total_rows += len(result_df)
            
            # Free up memory
            del df, result_df
            
        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")
    
    print(f"All data written to temporary CSV. Converting to Excel...")
    
    # Read CSV in chunks and write to Excel
    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        for chunk in pd.read_csv(TEMP_CSV, chunksize=2000000):
            chunk.to_excel(writer, sheet_name='Sheet1', index=False)
            break  # Only need one chunk since ExcelWriter will continue from there
    
    # Delete temporary CSV file
    if os.path.exists(TEMP_CSV):
        os.remove(TEMP_CSV)
    
    print("File processing complete!")
    return total_rows

if __name__ == "__main__":
    total_rows = process_files_with_chunking()
    print(f"Successfully created unified file with {total_rows} rows.")