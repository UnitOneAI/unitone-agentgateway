#!/bin/bash
set -e

# Cleanup Old Images Script for Unitone AgentGateway
# Usage: ./scripts/cleanup-old-images.sh [dev|staging|prod|all]

ENV=${1:-all}

# Environment-specific configuration
get_acr_name() {
    case $1 in
        dev) echo "unitoneagwdevacr" ;;
        staging) echo "unitoneagwstagingacr" ;;
        prod) echo "unitoneagwprodacr" ;;
        *) echo "Error: Invalid environment '$1'" >&2; return 1 ;;
    esac
}

cleanup_registry() {
    local env=$1
    local acr_name=$(get_acr_name $env)

    echo "================================"
    echo "Cleaning up $env environment"
    echo "Registry: $acr_name"
    echo "================================"

    # Get all tags except latest and recent ones
    echo "Fetching tags..."
    TAGS_TO_DELETE=$(az acr repository show-tags \
        --name "$acr_name" \
        --repository unitone-agentgateway \
        --orderby time_desc \
        --query "[10:]" \
        -o tsv 2>/dev/null || echo "")

    if [ -z "$TAGS_TO_DELETE" ]; then
        echo "No old tags to delete (keeping most recent 10)"
        return 0
    fi

    echo "Found $(echo "$TAGS_TO_DELETE" | wc -l) old tags to delete"
    echo ""
    echo "Tags to be deleted:"
    echo "$TAGS_TO_DELETE"
    echo ""

    read -p "Proceed with deletion? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping $env cleanup"
        return 0
    fi

    # Delete old tags
    while IFS= read -r tag; do
        if [ -n "$tag" ] && [ "$tag" != "latest" ]; then
            echo "Deleting: $tag"
            az acr repository delete \
                --name "$acr_name" \
                --image "unitone-agentgateway:$tag" \
                --yes 2>/dev/null || echo "  (failed or already deleted)"
        fi
    done <<< "$TAGS_TO_DELETE"

    echo "Cleanup complete for $env"
    echo ""
}

if [ "$ENV" == "all" ]; then
    for e in dev staging prod; do
        cleanup_registry $e
    done
else
    cleanup_registry $ENV
fi

echo "================================"
echo "Cleanup finished!"
echo "================================"
