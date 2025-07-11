#!/usr/bin/env python3
"""
K8s Reflexion Service Startup Script
Handles initialization, configuration validation, and service startup
"""
import os
import sys
import json
import asyncio
from pathlib import Path
import argparse
import yaml
import uvicorn
import structlog

# Load .env file if exists
from dotenv import load_dotenv
load_dotenv()

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

logger = structlog.get_logger()

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file {config_path} not found, using defaults")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file: {e}")
        sys.exit(1)

def validate_environment():
    """Validate required environment variables and dependencies"""
    issues = []
    
    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        issues.append("OPENAI_API_KEY environment variable not set")
    
    # Check if Go service URL is configured
    go_service_url = os.getenv("GO_SERVICE_URL", "http://localhost:8080")
    logger.info(f"Go service URL: {go_service_url}")
    
    # Check write permissions for logs and memory
    try:
        Path("./logs").mkdir(exist_ok=True)
        test_file = Path("./logs/test_write.tmp")
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        issues.append(f"Cannot write to logs directory: {e}")
    
    try:
        test_memory = Path("./test_memory.json")
        test_memory.write_text('{"test": true}')
        test_memory.unlink()
    except Exception as e:
        issues.append(f"Cannot write memory files: {e}")
    
    if issues:
        logger.error("Environment validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    
    logger.info("Environment validation passed")
    return True

def setup_logging(config: dict):
    """Setup structured logging based on configuration"""
    log_level = config.get("logging", {}).get("level", "INFO")
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add appropriate renderer based on format
    log_format = config.get("logging", {}).get("format", "console")
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set log level
    import logging
    logging.basicConfig(level=getattr(logging, log_level.upper()))

def print_startup_banner(config: dict):
    """Print startup banner with configuration summary"""
    banner = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        K8s Reflexion Service v{config.get('service', {}).get('version', '1.0.0')}                         ║
║                   Autonomous Kubernetes Error Resolution                     ║
║                      with LangGraph + Reflexion                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

🔧 Configuration:
   • Service Port: {config.get('service', {}).get('port', 8000)}
   • Go Service: {os.getenv('GO_SERVICE_URL', 'http://localhost:8080')}
   • OpenAI Model: {config.get('openai', {}).get('model', 'gpt-4-turbo-preview')}
   • Reflection Depth: {config.get('reflexion', {}).get('reflection_depth', 'medium')}
   • Debug Mode: {config.get('service', {}).get('debug', True)}

🧠 Reflexion Features:
   • Autonomous learning and strategy evolution
   • Multi-dimensional outcome observation
   • Deep self-analysis with LLM reflection
   • Episodic memory and pattern detection
   • Context-aware strategy selection

🚀 Starting service...
"""
    print(banner)

async def check_dependencies():
    """Check external service dependencies"""
    logger.info("Checking dependencies...")
    
    # Check Go service availability
    go_service_url = os.getenv("GO_SERVICE_URL", "http://localhost:8080")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{go_service_url}/health")
            if response.status_code == 200:
                logger.info("✅ Go service is reachable")
            else:
                logger.warning(f"⚠️ Go service returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ Go service not reachable: {e}")
        logger.info("Service will start but may have limited functionality")

def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description="K8s Reflexion Service")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Setup logging
    setup_logging(config)
    
    # Print banner
    print_startup_banner(config)
    
    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed, exiting")
        sys.exit(1)
    
    # Check dependencies
    asyncio.run(check_dependencies())
    
    # Determine service configuration
    host = args.host or config.get("service", {}).get("host", "0.0.0.0")
    port = args.port or config.get("service", {}).get("port", 8000)
    
    logger.info(f"Starting server on {host}:{port}")
    
    # Start the service
    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=args.reload,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()