import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main(
    repo_url: str = typer.Argument(..., help="Git repository URL to clone"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Specific branch, tag, or commit hash to clone"),
    no_build_isolation: bool = typer.Option(False, "--no-build-isolation", help="Disable build isolation for pip install"),
) -> None:
    """
    Clone a git repository to /app/comfy/custom_nodes and install its requirements.
    """
    logger.info(f"Starting node installation for repository: {repo_url}")
    if version:
        logger.info(f"Target version/branch/commit: {version}")
    if no_build_isolation:
        logger.info("Build isolation disabled for pip install")
    
    target_dir = Path("/app/comfy/custom_nodes")
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Target directory: {target_dir}")

    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    clone_path = target_dir / repo_name

    try:
        # Check if version looks like a commit hash (40 character hex string)
        is_commit_hash = version and len(version) == 40 and all(c in '0123456789abcdef' for c in version.lower())
        
        if is_commit_hash:
            logger.info(f"Detected commit hash format for version: {version}")
            # For commit hashes, use shallow clone but keep git functionality
            typer.echo(f"Cloning repository to {clone_path}...")
            logger.info(f"Starting commit-specific clone to {clone_path}")
            
            # Create the directory first
            clone_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize empty repo
            init_cmd = ["git", "init"]
            result = subprocess.run(init_cmd, cwd=clone_path, capture_output=True, text=True)
            if result.returncode != 0:
                typer.echo(f"Error initializing repository: {result.stderr}", err=True)
                raise typer.Exit(1)
            
            # Add remote
            remote_cmd = ["git", "remote", "add", "origin", repo_url]
            result = subprocess.run(remote_cmd, cwd=clone_path, capture_output=True, text=True)
            if result.returncode != 0:
                typer.echo(f"Error adding remote: {result.stderr}", err=True)
                raise typer.Exit(1)
            
            # Fetch the specific commit with depth 1
            typer.echo(f"Fetching commit {version}...")
            fetch_cmd = ["git", "fetch", "--depth", "1", "origin", version]
            result = subprocess.run(fetch_cmd, cwd=clone_path, capture_output=True, text=True)
            if result.returncode != 0:
                typer.echo(f"Error fetching commit: {result.stderr}", err=True)
                raise typer.Exit(1)
            
            # Checkout the commit
            checkout_cmd = ["git", "checkout", "FETCH_HEAD"]
            result = subprocess.run(checkout_cmd, cwd=clone_path, capture_output=True, text=True)
            if result.returncode != 0:
                typer.echo(f"Error checking out commit: {result.stderr}", err=True)
                raise typer.Exit(1)
            
            # Clean up to save space while keeping git functionality
            typer.echo("Cleaning up git objects to save space...")
            # Remove reflog to save space
            subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"], 
                         cwd=clone_path, capture_output=True)
            # Garbage collect and prune
            subprocess.run(["git", "gc", "--prune=now", "--aggressive"], 
                         cwd=clone_path, capture_output=True)
            
            # Initialize and update submodules if any
            submodule_cmd = ["git", "submodule", "update", "--init", "--recursive", "--depth", "1"]
            result = subprocess.run(submodule_cmd, cwd=clone_path, capture_output=True, text=True)
            # Don't fail if no submodules exist
        else:
            logger.info(f"Using standard clone approach for version: {version or 'default branch'}")
            # For branches and tags, use the original approach with depth=1
            clone_cmd = [
                "git", "clone",
                "--recursive",
                "--depth", "1"
            ]

            if version:
                clone_cmd.extend(["--branch", version])

            clone_cmd.extend([repo_url, str(clone_path)])

            logger.info(f"Executing git clone command: {' '.join(clone_cmd)}")
            typer.echo(f"Cloning repository to {clone_path}...")
            result = subprocess.run(clone_cmd, capture_output=True, text=True)
            
            if result.stdout:
                logger.debug(f"Git clone stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Git clone stderr: {result.stderr}")

            if result.returncode != 0:
                logger.error(f"Git clone failed with return code {result.returncode}")
                typer.echo(f"Error cloning repository: {result.stderr}", err=True)
                raise typer.Exit(1)

        logger.info("Git repository cloned successfully!")
        typer.echo("Repository cloned successfully!")

        requirements_file = clone_path / "requirements.txt"
        if requirements_file.exists():
            logger.info(f"Found requirements.txt at {requirements_file}")
            
            # Read and log requirements for visibility
            try:
                with open(requirements_file, 'r') as f:
                    requirements_content = f.read().strip()
                    if requirements_content:
                        logger.info(f"Requirements to install:\n{requirements_content}")
                    else:
                        logger.warning("requirements.txt is empty")
            except Exception as e:
                logger.warning(f"Could not read requirements.txt: {e}")
            
            pip_cmd = ["uv", "pip", "install", "-r", str(requirements_file)]

            if no_build_isolation:
                pip_cmd.append("--no-build-isolation")
                logger.info("Added --no-build-isolation flag to uv pip install")

            logger.info(f"Executing uv install command: {' '.join(pip_cmd)}")
            typer.echo("Installing requirements with uv...")
            
            result = subprocess.run(pip_cmd, capture_output=True, text=True)
            
            # Log the output for better debugging
            if result.stdout:
                logger.info(f"uv pip install stdout:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"uv pip install stderr:\n{result.stderr}")

            if result.returncode != 0:
                logger.error(f"uv pip install failed with return code {result.returncode}")
                typer.echo(f"Error installing requirements: {result.stderr}", err=True)
                raise typer.Exit(1)

            logger.info("uv pip install completed successfully!")
            typer.echo("Requirements installed successfully!")
        else:
            logger.info(f"No requirements.txt found at {requirements_file}")
            typer.echo("No requirements.txt found, skipping package installation.")

        logger.info(f"Node installation completed successfully at {clone_path}")
        typer.echo(f"Setup complete! Repository installed at {clone_path}")

    except Exception as e:
        logger.error(f"Node installation failed: {str(e)}", exc_info=True)
        typer.echo(f"An error occurred: {str(e)}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)