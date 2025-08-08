"""Command-line interface for Cursor Pro Model."""

import asyncio
import click
import json
import sys
from pathlib import Path
from typing import Optional

from .core.config import Config
from .core.model import CursorProModel
from .utils.file_utils import FileUtils
from .utils.logging_utils import setup_logging
from .parsers.factory import ParserFactory
from .api.server import create_app


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """Cursor Pro - AI-powered coding assistant."""
    ctx.ensure_object(dict)
    
    # Setup logging
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level=level)
    
    # Load configuration
    if config:
        ctx.obj['config'] = Config.load(config)
    else:
        ctx.obj['config'] = Config.from_env()


@cli.command()
@click.pass_context
def info(ctx):
    """Display system information."""
    config = ctx.obj['config']
    
    click.echo("Cursor Pro Model Information")
    click.echo("=" * 30)
    click.echo(f"Model: {config.model.name}")
    click.echo(f"Device: {config.model.device}")
    click.echo(f"GPU Enabled: {config.model.gpu_enabled}")
    click.echo(f"Max Tokens: {config.model.max_tokens}")
    click.echo(f"Supported Languages: {', '.join(config.code_analysis.supported_languages)}")
    
    # Check if model files exist
    model_dir = Path(config.model.cache_dir)
    if model_dir.exists():
        click.echo(f"Model Cache: {model_dir} (exists)")
    else:
        click.echo(f"Model Cache: {model_dir} (not found)")


@cli.command()
@click.option('--host', default='localhost', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--workers', default=1, help='Number of workers')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
@click.pass_context
def serve(ctx, host: str, port: int, workers: int, reload: bool):
    """Start the API server."""
    config = ctx.obj['config']
    
    click.echo(f"Starting Cursor Pro API server on {host}:{port}")
    
    try:
        import uvicorn
        uvicorn.run(
            "cursor_pro.api.server:app",
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            log_level="info"
        )
    except ImportError:
        click.echo("Error: uvicorn is required to run the server. Install with: pip install uvicorn")
        sys.exit(1)


@cli.command()
@click.argument('prompt')
@click.option('--language', '-l', default='python', help='Programming language')
@click.option('--max-tokens', '-m', default=None, type=int, help='Maximum tokens to generate')
@click.option('--temperature', '-t', default=None, type=float, help='Sampling temperature')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--context', multiple=True, help='Context files to include')
@click.pass_context
def generate(ctx, prompt: str, language: str, max_tokens: Optional[int], 
            temperature: Optional[float], output: Optional[str], context):
    """Generate code from a prompt."""
    config = ctx.obj['config']
    
    async def run_generation():
        model = CursorProModel(config)
        
        try:
            click.echo("Loading model...")
            await model.load_model()
            
            click.echo("Generating code...")
            result = await model.generate_code(
                prompt=prompt,
                language=language,
                max_tokens=max_tokens,
                temperature=temperature,
                context_files=list(context) if context else None
            )
            
            if output:
                # Save to file
                output_path = Path(output)
                await FileUtils.write_file_async(output_path, result)
                click.echo(f"Code saved to: {output_path}")
            else:
                # Print to stdout
                click.echo("\nGenerated Code:")
                click.echo("-" * 50)
                click.echo(result)
        
        finally:
            await model.unload_model()
    
    asyncio.run(run_generation())


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--position', '-p', default=None, type=int, help='Cursor position for completion')
@click.option('--max-suggestions', '-n', default=5, help='Maximum number of suggestions')
@click.pass_context
def complete(ctx, file_path: str, position: Optional[int], max_suggestions: int):
    """Provide code completions for a file."""
    config = ctx.obj['config']
    
    async def run_completion():
        model = CursorProModel(config)
        
        try:
            # Read file
            path = Path(file_path)
            content = await FileUtils.read_file_async(path)
            if content is None:
                click.echo(f"Error: Could not read file {file_path}")
                return
            
            # Determine position
            if position is None:
                position = len(content)  # End of file
            
            language = FileUtils.get_file_language(path)
            
            click.echo("Loading model...")
            await model.load_model()
            
            click.echo("Generating completions...")
            suggestions = await model.complete_code(
                code=content,
                cursor_position=position,
                language=language
            )
            
            click.echo(f"\nCompletions for {file_path} at position {position}:")
            click.echo("-" * 50)
            for i, suggestion in enumerate(suggestions[:max_suggestions], 1):
                click.echo(f"{i}. {suggestion}")
        
        finally:
            await model.unload_model()
    
    asyncio.run(run_completion())


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--detail', '-d', default='medium', help='Detail level: basic, medium, detailed')
@click.pass_context
def explain(ctx, file_path: str, detail: str):
    """Explain code in a file."""
    config = ctx.obj['config']
    
    async def run_explanation():
        model = CursorProModel(config)
        
        try:
            # Read file
            path = Path(file_path)
            content = await FileUtils.read_file_async(path)
            if content is None:
                click.echo(f"Error: Could not read file {file_path}")
                return
            
            language = FileUtils.get_file_language(path)
            
            click.echo("Loading model...")
            await model.load_model()
            
            click.echo("Generating explanation...")
            explanation = await model.explain_code(
                code=content,
                language=language
            )
            
            click.echo(f"\nExplanation for {file_path}:")
            click.echo("-" * 50)
            click.echo(explanation)
        
        finally:
            await model.unload_model()
    
    asyncio.run(run_explanation())


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--format', '-f', default='json', type=click.Choice(['json', 'text']), help='Output format')
@click.pass_context
def analyze(ctx, file_path: str, format: str):
    """Analyze a code file."""
    
    async def run_analysis():
        # Read file
        path = Path(file_path)
        content = await FileUtils.read_file_async(path)
        if content is None:
            click.echo(f"Error: Could not read file {file_path}")
            return
        
        language = FileUtils.get_file_language(path)
        parser = ParserFactory.create_parser(language)
        
        if not parser:
            click.echo(f"Error: No parser available for language {language}")
            return
        
        # Parse file
        result = parser.parse(content, str(path))
        
        if format == 'json':
            # JSON output
            output = {
                'file_path': str(path),
                'language': language,
                'symbols': [symbol.__dict__ for symbol in result.symbols],
                'dependencies': [dep.__dict__ for dep in result.dependencies],
                'issues': [issue.__dict__ for issue in result.issues],
                'metrics': result.metrics
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Text output
            click.echo(f"Analysis for {file_path}")
            click.echo("=" * 50)
            click.echo(f"Language: {language}")
            click.echo(f"Symbols: {len(result.symbols)}")
            click.echo(f"Dependencies: {len(result.dependencies)}")
            click.echo(f"Issues: {len(result.issues)}")
            
            if result.metrics:
                click.echo("\nMetrics:")
                for key, value in result.metrics.items():
                    click.echo(f"  {key}: {value}")
            
            if result.issues:
                click.echo("\nIssues:")
                for issue in result.issues[:10]:  # Show first 10 issues
                    click.echo(f"  Line {issue.line}: {issue.message} ({issue.severity})")
    
    asyncio.run(run_analysis())


@cli.command()
@click.argument('workspace_path', type=click.Path(exists=True))
@click.option('--max-files', default=100, help='Maximum files to analyze')
@click.option('--format', '-f', default='text', type=click.Choice(['json', 'text']), help='Output format')
@click.pass_context
def workspace(ctx, workspace_path: str, max_files: int, format: str):
    """Analyze a workspace."""
    
    async def run_workspace_analysis():
        path = Path(workspace_path)
        
        click.echo(f"Analyzing workspace: {path}")
        
        # Get workspace statistics
        stats = await FileUtils.get_directory_stats(path)
        
        # Discover files
        files = await FileUtils.discover_files(path, max_files=max_files)
        
        if format == 'json':
            output = {
                'workspace_path': str(path),
                'stats': stats,
                'files': [str(f) for f in files]
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"\nWorkspace Statistics:")
            click.echo(f"  Total files: {stats['total_files']}")
            click.echo(f"  Total size: {stats['total_size']} bytes")
            click.echo(f"  Directories: {stats['directories']}")
            
            if stats['languages']:
                click.echo(f"\nLanguages:")
                for lang, count in sorted(stats['languages'].items(), key=lambda x: x[1], reverse=True):
                    click.echo(f"  {lang}: {count} files")
            
            click.echo(f"\nDiscovered {len(files)} code files (max: {max_files})")
    
    asyncio.run(run_workspace_analysis())


@cli.command()
@click.pass_context
def test(ctx):
    """Run basic functionality tests."""
    config = ctx.obj['config']
    
    async def run_tests():
        click.echo("Running Cursor Pro tests...")
        
        # Test 1: Model loading
        click.echo("1. Testing model loading...")
        try:
            model = CursorProModel(config)
            await model.load_model()
            health = await model.health_check()
            
            if health['model_loaded']:
                click.echo("   ✓ Model loaded successfully")
            else:
                click.echo("   ✗ Model failed to load")
                return
            
            await model.unload_model()
            click.echo("   ✓ Model unloaded successfully")
        except Exception as e:
            click.echo(f"   ✗ Model test failed: {e}")
            return
        
        # Test 2: Parser functionality
        click.echo("2. Testing parsers...")
        test_code = "def hello_world():\n    print('Hello, World!')\n"
        parser = ParserFactory.create_parser('python')
        
        if parser:
            result = parser.parse(test_code)
            if result.symbols:
                click.echo("   ✓ Parser working correctly")
            else:
                click.echo("   ✗ Parser not extracting symbols")
        else:
            click.echo("   ✗ Parser not available")
        
        # Test 3: File utilities
        click.echo("3. Testing file utilities...")
        try:
            test_path = Path("/tmp/cursor_pro_test.py")
            success = await FileUtils.write_file_async(test_path, test_code)
            if success:
                content = await FileUtils.read_file_async(test_path)
                if content == test_code:
                    click.echo("   ✓ File operations working")
                    test_path.unlink()  # Clean up
                else:
                    click.echo("   ✗ File read/write mismatch")
            else:
                click.echo("   ✗ File write failed")
        except Exception as e:
            click.echo(f"   ✗ File test failed: {e}")
        
        click.echo("\nTests completed!")
    
    asyncio.run(run_tests())


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()