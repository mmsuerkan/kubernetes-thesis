#!/bin/bash
# Log management script for K8s Reflexion System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  tail         Show real-time logs for all services"
    echo "  follow       Follow logs for specific service"
    echo "  export       Export logs to files"
    echo "  analyze      Analyze logs for errors and patterns"
    echo "  status       Show service health status"
    echo ""
    echo "Options:"
    echo "  -s, --service SERVICE    Specify service (reflexion-service, pod-watcher)"
    echo "  -l, --lines NUM          Number of lines to show (default: 100)"
    echo "  -f, --filter PATTERN     Filter logs by pattern"
    echo "  -o, --output FILE        Output file for export"
    echo ""
    echo "Examples:"
    echo "  $0 tail                          # Show all service logs"
    echo "  $0 follow -s reflexion-service   # Follow Python service logs"
    echo "  $0 export -o logs.txt            # Export all logs"
    echo "  $0 analyze                       # Analyze for errors"
}

# Function to check if docker-compose is running
check_services() {
    if ! docker-compose ps | grep -q "Up"; then
        print_color $RED "❌ Services are not running. Start them with: docker-compose up -d"
        exit 1
    fi
}

# Function to show real-time logs for all services
tail_all_logs() {
    local lines=${1:-100}
    print_color $GREEN "📋 Showing logs for all services (last $lines lines)..."
    docker-compose logs --tail=$lines -f
}

# Function to follow logs for specific service
follow_service_logs() {
    local service=$1
    local lines=${2:-100}
    local filter=${3:-""}
    
    if [[ -z "$service" ]]; then
        print_color $RED "❌ Service name required"
        show_usage
        exit 1
    fi
    
    print_color $GREEN "📋 Following logs for $service (last $lines lines)..."
    
    if [[ -n "$filter" ]]; then
        docker-compose logs --tail=$lines -f $service | grep --color=always "$filter"
    else
        docker-compose logs --tail=$lines -f $service
    fi
}

# Function to export logs to files
export_logs() {
    local output_dir=${1:-"logs_$(date +%Y%m%d_%H%M%S)"}
    mkdir -p "$output_dir"
    
    print_color $GREEN "📤 Exporting logs to $output_dir/..."
    
    # Export logs for each service
    docker-compose logs reflexion-service > "$output_dir/reflexion-service.log" 2>&1
    docker-compose logs pod-watcher > "$output_dir/pod-watcher.log" 2>&1
    
    # Create combined log
    docker-compose logs > "$output_dir/combined.log" 2>&1
    
    # Create summary
    cat << EOF > "$output_dir/summary.txt"
Log Export Summary
==================
Date: $(date)
Services: reflexion-service, pod-watcher

Files:
- reflexion-service.log: Python Reflexion service logs
- pod-watcher.log: Go pod watcher logs  
- combined.log: All services combined
- summary.txt: This summary file

Log Analysis:
- Total lines: $(wc -l "$output_dir/combined.log" | awk '{print $1}')
- Error count: $(grep -i error "$output_dir/combined.log" | wc -l)
- Success count: $(grep -i success "$output_dir/combined.log" | wc -l)
EOF
    
    print_color $GREEN "✅ Logs exported to $output_dir/"
}

# Function to analyze logs for errors and patterns
analyze_logs() {
    print_color $GREEN "🔍 Analyzing logs for errors and patterns..."
    
    echo ""
    print_color $YELLOW "=== ERROR ANALYSIS ==="
    docker-compose logs | grep -i "error\|failed\|exception" | tail -10
    
    echo ""
    print_color $YELLOW "=== SUCCESS PATTERNS ==="
    docker-compose logs | grep -i "success\|completed\|✅" | tail -5
    
    echo ""
    print_color $YELLOW "=== REFLEXION PROCESSING ==="
    docker-compose logs reflexion-service | grep -i "processing pod error\|strategy selection\|yaml manifest" | tail -5
    
    echo ""
    print_color $YELLOW "=== POD WATCHER ACTIVITY ==="
    docker-compose logs pod-watcher | grep -i "processing failed pod\|scanning.*pods" | tail -5
    
    echo ""
    print_color $YELLOW "=== HEALTH STATUS ==="
    docker-compose ps
}

# Function to show service health status
show_status() {
    print_color $GREEN "📊 Service Health Status"
    echo ""
    
    # Show docker-compose status
    docker-compose ps
    
    echo ""
    print_color $YELLOW "=== Service Endpoints ==="
    echo "Reflexion Service: http://localhost:8000"
    echo "Pod Watcher: http://localhost:8080"
    
    echo ""
    print_color $YELLOW "=== Health Checks ==="
    
    # Check reflexion service health
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_color $GREEN "✅ Reflexion Service: Healthy"
    else
        print_color $RED "❌ Reflexion Service: Unhealthy"
    fi
    
    # Check pod watcher health
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        print_color $GREEN "✅ Pod Watcher: Healthy"
    else
        print_color $RED "❌ Pod Watcher: Unhealthy"
    fi
}

# Parse command line arguments
COMMAND=""
SERVICE=""
LINES=100
FILTER=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        tail|follow|export|analyze|status)
            COMMAND="$1"
            shift
            ;;
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -l|--lines)
            LINES="$2"
            shift 2
            ;;
        -f|--filter)
            FILTER="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_color $RED "❌ Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    tail)
        check_services
        tail_all_logs $LINES
        ;;
    follow)
        check_services
        follow_service_logs $SERVICE $LINES $FILTER
        ;;
    export)
        check_services
        export_logs $OUTPUT
        ;;
    analyze)
        check_services
        analyze_logs
        ;;
    status)
        show_status
        ;;
    "")
        print_color $RED "❌ No command specified"
        show_usage
        exit 1
        ;;
    *)
        print_color $RED "❌ Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac