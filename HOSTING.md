# Running, updating and hosting DIC Studio

Local execution and public hosting use the same Python server. Choose one
hosting path; the repository does not install or configure a macOS background
service or tunnel automatically. Earlier zrok and partial-ZIP instructions in
`EXPERIMENT_UPGRADE.md` are historical.

## Local use and updates

From the project directory, activate the Python environment you installed the
requirements into, then run:

```bash
python main.py
```

The default address is `http://127.0.0.1:8765`. To check the running server, use
GET (HEAD requests are not supported):

```bash
curl --max-time 5 http://127.0.0.1:8765/healthz
```

Expected response: `{"status": "ok"}`. This checks the Python server, not the
public tunnel, DNS or experiment accuracy.

After a pull request is merged, save/commit your own local work first, then:

```bash
git pull --ff-only origin main
python -m pip install -r requirements.txt
```

Restart the existing server process to load Python changes, then hard-refresh
the browser to load updated JavaScript/HTML. For a manually started server,
Ctrl+C stops it; run `python main.py` again. If your Mac already has a configured
background service, restart that service instead of starting a second server on
the same port. This repository does not prescribe its service name or path.
Download any important active results before restarting: sessions are in memory.

## Hosting from an always-on Mac

A public reverse proxy/tunnel forwards an HTTPS address to the local server at
`http://127.0.0.1:8765`. The server, tunnel service and internet connection must
remain running, and the Mac must remain awake. Closing VS Code is only safe
when those processes are managed independently of its terminal. A GitHub push
alone does not update or restart the Mac's running copy.

Tailscale Funnel is one option. Follow the current
[official Funnel setup instructions](https://tailscale.com/docs/features/tailscale-funnel)
for installation, permissions and public sharing. Use the public address printed
by the configured tunnel; a private tailnet address is not a substitute for
public sharing. This guide does not assert that a particular public hostname is
currently reachable. Verify the public `/healthz` URL from another network after
checking local health. Do not restart/recreate tunnels merely because the local
server is healthy; first inspect the tunnel's status and the actual public error.

## Render alternative

`render.yaml` is an optional single-instance deployment template, not a
requirement for local/Mac hosting. Connect this repository as a Blueprint and
review its settings before deploying. The tracked template specifies:

- Python 3.12.12 and `pip install -r requirements.txt`.
- Start: `python lab_server.py --host 0.0.0.0 --no-browser`.
- Health endpoint: `/healthz`; the platform supplies `PORT`.
- `LAB_COOKIE_SECURE=1`, `MPLBACKEND=Agg`, and one BLAS/OpenMP thread.
- `plan: free`; verify availability and current service limits with the provider.

For a manual Web Service, use the same build/start commands and environment
variables. Use the actual deployed URL. Automatic deployment must be enabled
in the provider settings if pushes should redeploy the service. A redeploy
restarts the server and clears in-memory sessions.

## Visitor sessions, storage and limits

One calculation worker handles up to four pending/running jobs in total. Each
browser session can have one active job. Regular tabs in the same browser
profile share a session; another browser/private window gets a separate session.
There is no account/login system. Run assets require the owning session, so a
copied download link does not grant another visitor access.

The latest five runs per session are retained. At most 64 sessions are held;
inactive sessions expire after six hours and cleanup runs on later requests.
Active calculations do not expire. Restarting loses session access even when
old run files remain on disk; download important results while the session is
available. Storage on a hosted platform depends on its configuration. Keep a
single server instance because sessions are in memory.

Verify a deployment by running different specimens in two separate browser
sessions, opening field comparisons and downloading each run. Verify public
access separately from local access. See `tests/README.md` for automated checks.
