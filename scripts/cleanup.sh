set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
DAGSTER_HOME_DIR="$ROOT/.dagster_home"
MINIO_CONTAINER="${MINIO_CONTAINER:-wrc_minio}"
MC_ALIAS="cleanup"

ASSUME_YES=0
for argument in "$@"; do
    case "$argument" in
        -y|--yes) ASSUME_YES=1 ;;
        -h|--help) sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $argument (try --help)" >&2; exit 2 ;;
    esac
done

setting() {
    local key=$1 default=$2 value=""
    if [[ -f "$ENV_FILE" ]]; then
        value=$(grep -E "^[[:space:]]*${key}=" "$ENV_FILE" | tail -1 | cut -d= -f2- \
                | sed -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")
    fi
    printf '%s' "${value:-$default}"
}

MONGO_URI=$(setting MONGO_URI "mongodb://localhost:27017")
MONGO_DATABASE=$(setting MONGO_DATABASE "wrc")
LANDING_BUCKET=$(setting LANDING_BUCKET "landing")
CURATED_BUCKET=$(setting CURATED_BUCKET "curated")
MINIO_ACCESS_KEY=$(setting MINIO_ACCESS_KEY "minioadmin")
MINIO_SECRET_KEY=$(setting MINIO_SECRET_KEY "minioadmin")

#  preflight 

command -v mongosh >/dev/null || { echo "mongosh not found on PATH" >&2; exit 1; }

mongosh "$MONGO_URI" --quiet --eval 'quit(0)' >/dev/null 2>&1 \
    || { echo "cannot reach mongo at $MONGO_URI" >&2; exit 1; }

docker exec "$MINIO_CONTAINER" true >/dev/null 2>&1 \
    || { echo "container '$MINIO_CONTAINER' is not running; try: docker compose up -d" >&2; exit 1; }

docker exec "$MINIO_CONTAINER" \
    mc alias set "$MC_ALIAS" "http://127.0.0.1:9000" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null

if pgrep -f "dagster dev" >/dev/null 2>&1; then
    echo "warning: 'dagster dev' is running. Stop it first, or it will rewrite the history you delete."
    echo
fi

mongo_server=$(mongosh "$MONGO_URI" --quiet --eval 'print(db.version())')
mongo_summary=$(mongosh "$MONGO_URI/$MONGO_DATABASE" --quiet --eval '
    const names = db.getCollectionNames();
    print(names.length ? names.map(c => c + ": " + db[c].countDocuments({})).join(", ") : "no collections");
')

bucket_summary() {
    local bucket=$1
    if docker exec "$MINIO_CONTAINER" mc ls "$MC_ALIAS/$bucket" >/dev/null 2>&1; then
        printf '%s objects' "$(docker exec "$MINIO_CONTAINER" mc ls --recursive "$MC_ALIAS/$bucket" 2>/dev/null | wc -l | tr -d ' ')"
    else
        printf 'absent'
    fi
}

cat <<SUMMARY
About to permanently remove:

  MongoDB   $MONGO_URI  (mongod $mongo_server)
            drop database '$MONGO_DATABASE' — $mongo_summary
  MinIO     container $MINIO_CONTAINER
            remove bucket '$LANDING_BUCKET' ($(bucket_summary "$LANDING_BUCKET"))
            remove bucket '$CURATED_BUCKET' ($(bucket_summary "$CURATED_BUCKET"))
  Dagster   $DAGSTER_HOME_DIR
            run history, event logs and schedules (dagster.yaml is kept)

SUMMARY

if [[ $ASSUME_YES -eq 0 ]]; then
    read -r -p "Type 'yes' to proceed: " reply
    [[ "$reply" == "yes" ]] || { echo "aborted; nothing was removed"; exit 1; }
    echo
fi

#  mongo 

mongosh "$MONGO_URI/$MONGO_DATABASE" --quiet --eval 'db.dropDatabase()' >/dev/null
echo "  mongo    dropped database '$MONGO_DATABASE'"

#  object storage 

for bucket in "$LANDING_BUCKET" "$CURATED_BUCKET"; do
    if docker exec "$MINIO_CONTAINER" mc ls "$MC_ALIAS/$bucket" >/dev/null 2>&1; then
        # rb --force removes the objects and the bucket itself; ensure_bucket() recreates it next run
        docker exec "$MINIO_CONTAINER" mc rb --force "$MC_ALIAS/$bucket" >/dev/null
        echo "  minio    removed bucket '$bucket'"
    else
        echo "  minio    bucket '$bucket' already absent"
    fi
done

#  dagster 

if [[ -d "$DAGSTER_HOME_DIR" ]]; then
    # everything except dagster.yaml, which is configuration rather than run state
    find "$DAGSTER_HOME_DIR" -mindepth 1 -maxdepth 1 ! -name dagster.yaml -exec rm -rf {} +
    echo "  dagster  cleared run history in $DAGSTER_HOME_DIR"
else
    echo "  dagster  $DAGSTER_HOME_DIR does not exist"
fi

#  crawl scratch space 

CRAWL_WORKSPACE_DIR=$(setting CRAWL_WORKSPACE_DIR "/tmp/wrc_pipeline_crawls")
if [[ -d "$CRAWL_WORKSPACE_DIR" ]]; then
    # normally deleted per partition in a finally block; leftovers mean a crawl was killed mid-run
    leftovers=$(find "$CRAWL_WORKSPACE_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    rm -rf "${CRAWL_WORKSPACE_DIR:?}"/*
    echo "  crawl    cleared $leftovers leftover workspace(s) in $CRAWL_WORKSPACE_DIR"
fi

echo
echo "Done. The next run recreates the buckets and indexes."
