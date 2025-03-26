import json
import os
from huggingface_hub import hf_hub_download
import argparse

def download_model(model_config):
    """
    Download a model file from Hugging Face based on the configuration.
    
    Args:
        model_config (dict): Dictionary containing model configuration
            Required keys:
            - repo_id: Hugging Face repository ID
            - filename: Name of the file to download
            - local_path: Local path where the file should be saved
            - branch: Branch name (optional, defaults to 'main')
    """
    repo_id = model_config['repo_id']
    subfolder = model_config['subfolder']
    filename = model_config['filename']
    local_path = model_config['local_path']
    
    # Check if file already exists - need to check the actual download location
    downloaded_path = filename
    if os.path.exists(local_path):
        print(f"File already exists at {local_path}, skipping download")
        return
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    print(f"Downloading {filename} from {repo_id} to {local_path}")
    
    try:
        hf_hub_download(
            repo_id=repo_id,
            subfolder=subfolder,
            filename=filename,
            local_dir=os.path.dirname(local_path)
        )
        
        # Rename the file to match the desired local_path
        downloaded_path = os.path.join(os.path.dirname(local_path), subfolder,  filename)
        if downloaded_path != local_path:
            os.rename(downloaded_path, local_path)
            
        print(f"Successfully downloaded {filename} to {local_path}")
    except Exception as e:
        print(f"Error downloading {filename}: {str(e)}")

def main():
    """
    Main function to download models from Hugging Face based on JSON configuration.
    """
    parser = argparse.ArgumentParser(description='Download models from Hugging Face based on JSON configuration')
    parser.add_argument('config_file', help='Path to the JSON configuration file')
    args = parser.parse_args()
    
    # Read the configuration file
    with open(args.config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Download each model specified in the configuration
    for model_config in config:
        download_model(model_config)

if __name__ == '__main__':
    main()
