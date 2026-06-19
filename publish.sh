set -Eeuo pipefail
git init
git add .
git commit -m "feat: APVA Phase 2 MVP - API, SDK, CLI, tests" || git commit -m "chore: finalize Phase 2 artifacts" || true
gh repo create apva-framework --public --source=. --remote=origin --push