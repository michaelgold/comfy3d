import torch
from safetensors.torch import save_file
import typer
from pathlib import Path
from typing import Optional
from rich import print
from rich.progress import track


app = typer.Typer(help="Convert .pt PyTorch model to .safetensors file")


def extract_state_dict(checkpoint):
    """Extract weights depending on the structure."""
    if isinstance(checkpoint, torch.nn.Module):
        return checkpoint.state_dict()
    elif isinstance(checkpoint, dict):
        if "state_dict" in checkpoint:
            return checkpoint["state_dict"]
        elif "model" in checkpoint:
            return checkpoint["model"]
        else:
            return checkpoint
    else:
        raise ValueError("Unrecognized checkpoint format. Expected dict or nn.Module.")


@app.command()
def convert(
    pt_file: Path = typer.Argument(..., help="Path to the .pt or TorchScript file"),
    output_file: Path = typer.Argument(..., help="Where to save the cleaned .safetensors"),
    prefix: Optional[str] = typer.Option(None, help="Only include keys starting with this prefix (e.g., 'generator.')"),
    strip_prefix: bool = typer.Option(True, help="Strip the prefix from keys"),
    dry_run: bool = typer.Option(False, help="Preview matching keys only (no output written)"),
):
    """
    Convert a .pt file to .safetensors, optionally filtering keys by prefix.
    Works with both state_dict and TorchScript files.
    """
    if not pt_file.exists():
        print(f"[red]❌ .pt file not found: {pt_file}[/red]")
        raise typer.Exit(1)

    print(f"[cyan]🔍 Loading checkpoint from:[/cyan] {pt_file}")
    try:
        checkpoint = torch.load(pt_file, map_location="cpu")  # For plain state_dicts
    except RuntimeError as e:
        if "TorchScript" in str(e):
            print("[yellow]⚠️ TorchScript archive detected. Using torch.jit.load()[/yellow]")
            checkpoint = torch.jit.load(pt_file, map_location="cpu")
        else:
            raise

    try:
        state_dict = extract_state_dict(checkpoint)
    except Exception as e:
        print(f"[red]❌ Failed to extract weights: {e}[/red]")
        raise typer.Exit(1)

    matched_keys = {}
    skipped_keys = {}

    for k, v in track(state_dict.items(), description="🔧 Filtering keys..."):
        if prefix:
            if k.startswith(prefix):
                new_key = k[len(prefix):] if strip_prefix else k
                matched_keys[new_key] = v
            else:
                skipped_keys[k] = v
        else:
            matched_keys[k] = v

    print(f"\n[green]✅ Matched {len(matched_keys)} keys[/green]")
    if skipped_keys:
        print(f"[yellow]⚠️ Skipped {len(skipped_keys)} keys[/yellow]")
        for example in list(skipped_keys.keys())[:5]:
            print(f"  - {example}")

    if dry_run:
        print("[blue]ℹ️ Dry run mode: no file written.[/blue]")
        return

    try:
        save_file(matched_keys, str(output_file))
        print(f"[bold green]🎉 Saved safetensors file to: {output_file}[/bold green]")
    except Exception as e:
        print(f"[red]❌ Failed to save safetensors: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
