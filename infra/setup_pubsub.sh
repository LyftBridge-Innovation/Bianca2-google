#!/usr/bin/env bash
# One-time Google Cloud infrastructure setup for the Email Agent.
# Run this ONCE before deploying for the first time.
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   export REGION=us-central1
#   export CLOUD_RUN_URL=https://bianca-backend-xxxx-uc.a.run.app
#   bash infra/setup_pubsub.sh

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
CLOUD_RUN_URL="${CLOUD_RUN_URL:?Set CLOUD_RUN_URL (your Cloud Run service URL)}"

TOPIC="gmail-push"
SUBSCRIPTION="gmail-push-sub"
SERVICE_ACCOUNT="bianca-backend-sa"
SA_EMAIL="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Project : $PROJECT_ID"
echo "==> Region  : $REGION"
echo "==> Cloud Run URL: $CLOUD_RUN_URL"
echo ""

# ── 1. Create Pub/Sub topic ───────────────────────────────────────────────────
echo "[1/6] Creating Pub/Sub topic '${TOPIC}'..."
gcloud pubsub topics create "${TOPIC}" --project="${PROJECT_ID}" 2>/dev/null || \
  echo "      (already exists, skipping)"

# ── 2. Grant Gmail service account publish rights ─────────────────────────────
echo "[2/6] Granting Gmail publish rights to topic..."
gcloud pubsub topics add-iam-policy-binding "${TOPIC}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

# ── 3. Create (or update) push subscription → Cloud Run ─────────────────────
WEBHOOK_URL="${CLOUD_RUN_URL}/gmail/webhook"
echo "[3/6] Creating push subscription '${SUBSCRIPTION}' → ${WEBHOOK_URL}..."
gcloud pubsub subscriptions create "${SUBSCRIPTION}" \
  --project="${PROJECT_ID}" \
  --topic="${TOPIC}" \
  --push-endpoint="${WEBHOOK_URL}" \
  --ack-deadline=60 \
  2>/dev/null || \
  gcloud pubsub subscriptions modify-push-config "${SUBSCRIPTION}" \
    --project="${PROJECT_ID}" \
    --push-endpoint="${WEBHOOK_URL}"

# ── 4. Create service account for Cloud Run (if not exists) ──────────────────
echo "[4/6] Ensuring service account '${SA_EMAIL}'..."
gcloud iam service-accounts create "${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --display-name="Bianca Backend" \
  2>/dev/null || echo "      (already exists, skipping)"

# ── 5. Grant required IAM roles ───────────────────────────────────────────────
echo "[5/6] Granting IAM roles to service account..."
for ROLE in \
  "roles/datastore.user" \
  "roles/pubsub.subscriber" \
  "roles/run.invoker" \
  "roles/aiplatform.user" \
  "roles/discoveryengine.admin"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --quiet
done

# ── 6. Create Artifact Registry repository (if not exists) ───────────────────
echo "[6/6] Ensuring Artifact Registry repository 'bianca'..."
gcloud artifacts repositories create bianca \
  --project="${PROJECT_ID}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Bianca backend images" \
  2>/dev/null || echo "      (already exists, skipping)"

echo ""
echo "==> Setup complete."
echo ""
echo "Next steps:"
echo "  1. Deploy to Cloud Run (first time):"
echo "     gcloud run deploy bianca-backend \\"
echo "       --source . \\"
echo "       --region ${REGION} \\"
echo "       --service-account ${SA_EMAIL} \\"
echo "       --allow-unauthenticated \\"
echo "       --port 8080 \\"
echo "       --set-env-vars GCP_PROJECT_ID=${PROJECT_ID},GMAIL_PUBSUB_TOPIC=projects/${PROJECT_ID}/topics/${TOPIC}"
echo ""
echo "  2. After deploy, update CLOUD_RUN_URL and re-run this script if the URL changed."
echo ""
echo "  3. In Neural Config → Integrations → Email Agent:"
echo "     - Create a Gmail label (e.g. 'Bianca_Contacts')"
echo "     - Set up a Gmail filter to route emails to that label"
echo "     - Enter the label name and click 'Enable Agent'"
