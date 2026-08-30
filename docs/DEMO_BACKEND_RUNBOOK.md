# Connecting the demo to the live backend

This is the operator runbook for wiring the Cloudflare demo site to the
product backend on Google Cloud Run, so testers on phones exercise real
backend behavior. The authoritative deployment documents are the ones in the
founder's backend connection package (`CLOUDFLARE_WIRING.md`,
`deploy_cloud_run.sh`, `.env.example`); this file maps those steps onto this
repository and records what each side owns.

## What this repository already carries

- `lib/api/forge_api_client.dart`: the live client. It reads
  `FORGE_API_BASE_URL` at compile time, fails at startup if a live build is
  misconfigured, resolves every failure to a consumer-safe denial, and never
  retries a write.
- A live-connection banner on the dashboard. It renders nothing in the pure
  fixture demo, "Live backend connected" when the health endpoint answers ok,
  and a fail-closed notice when it does not.
- The repository seam (`lib/api/forge_repository.dart`): screens read
  providers, so moving a feature from fixtures to the live backend is a
  provider change, not a screen change.

Without `FORGE_API_BASE_URL` at build time, the app is exactly the fixture
demo it has always been. Nothing live is shown or implied.

## Operator steps (Google Cloud side, from the connection package)

1. Deploy the three internal services the backend depends on, each with
   `--ingress internal --no-allow-unauthenticated`. The backend refuses to
   start without their URLs and reports degraded health if any is
   unreachable. **Their source is not in this repository or in the two
   connection packages; they deploy from their own repositories.**
2. Create the client secret in Secret Manager (`openssl rand -hex 32`).
   Never place it in this repository, a plaintext Pages variable, or chat.
3. Deploy the product backend with `deploy_cloud_run.sh` (it runs its own
   test, lint, and security gates before building).
4. Put a Cloudflare Worker reverse proxy on your API hostname (option 4a in
   `CLOUDFLARE_WIRING.md`). The Worker injects the client secret as an
   encrypted Worker secret, hides the Cloud Run URL, and makes browser calls
   same-origin.
5. Set `FORGE_ALLOWED_ORIGINS` to the Pages domains.

## Connecting this repository (my side, once you send the API hostname)

The public API hostname (for example `https://api.yourdomain.com`) is not a
secret. Send it here and the web bundle is rebuilt with:

```bash
flutter build web --release --base-href /demo/ \
  --dart-define=FORGE_API_BASE_URL=https://api.yourdomain.com
```

and pushed, which redeploys the Cloudflare demo. The dashboard banner then
reports the live edge's real health.

## Verification order (from the wiring document)

1. `curl https://api.yourdomain.com/health`: expect ok with all dependencies
   ok.
2. An unauthenticated write returns 401.
3. A stopped internal service surfaces as a 503 denial, never a success.
4. No internal system name appears in any response body.

## Honest scope for the tester program

The backend in the connection package implements the governed write path
(evaluate, epoch, stage, commit, single-call governed write) and health, with
exports gated off pending schema confirmation. Its own documentation states
that login and the dashboard data endpoints are not implemented. That means:

- Testers can exercise every screen of the demo today on fixtures, plus the
  live health connection and, once wired to a screen, the live governed
  write and evaluation flows with real fail-closed behavior.
- Feed, opportunities, profiles, rewards, vouching, chat, and notifications
  remain fixture-backed until those consumer endpoints exist server-side.
  This is PR item 10 (backend enforcement) and is the gap between the
  Cloudflare tester demo and the full FIU pilot deployment.
- Accounts for real students (the 18 to 35 FIU cohort) additionally require
  the identity provider decision the backend documentation lists as open,
  plus the counsel items already tracked in the PR.
