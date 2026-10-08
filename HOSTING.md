**Apply this update**

Copy lab_server.py, render.yaml and HOSTING.md into your project root. Copy the supplied test files into tests/. The current web/ folder from the stress-colour release already works with this server. Local use remains python main.py.

**Push to GitHub**

Inside your project folder:

```bash
git add lab_server.py render.yaml HOSTING.md tests/test_server.py tests/test_hosting.py tests/ui_controller.cjs
git commit -m "Prepare lab for Render hosting with separate visitor sessions"
git push
```

**Render: automatic configuration**

1. Sign in to https://render.com with GitHub.
2. Choose New → Blueprint and connect AkshithValisemmagari/DIC-Mechanics-of-Solids.
3. Select main. Render reads render.yaml at the repository root.
4. Review the service and create/deploy the Blueprint. The file selects a Free plan.
5. Once live, open the actual onrender.com address shown by Render.

**Render: manual Web Service alternative**

Connect the repository using New → Web Service. Set Python runtime, main branch, blank root directory, build command pip install -r requirements.txt, and start command python lab_server.py --host 0.0.0.0 --no-browser. Set health check /healthz. Add all environment variables listed in render.yaml. Enable automatic deployment on commits. Render provides PORT automatically.

**Verify**

Run one experiment, check the 3D stress colours and Field comparison, and download its ZIP. Open a private/incognito browser window and run a different specimen. Each session must retain its own status, result, images and downloads. Regular tabs in the same browser profile intentionally share a session. Reloading the page retains the latest result while the server and session remain alive.

**Storage and limits**

This is a single-instance deployment. Sessions are held in server memory, and the single calculation worker queues up to four jobs in total. One browser session can have one active job; a full queue returns a retry message. There is no account/login system. Session cookies identify access to run files; copied run links cannot be opened in another browser session.

Results are temporary. Server restarts, redeploys and free-service sleep can lose sessions/results; download important results before leaving. The latest five runs per session are retained; older run downloads are removed. At most 64 sessions are kept at once. Inactive sessions expire after six hours, with their run files removed when a later request triggers cleanup. Active calculations do not expire. Free hosting may pause when idle and take time to wake. Persistent storage and result history are separate future additions. Keep one instance because sessions are in memory.

**Future changes**

Test locally, commit changes and git push. With auto-deploy enabled, Render deploys the latest main commit at the same website address. A deployment resets current sessions, so finish/download active experiments first.

**Checks**

python -m unittest discover -s tests -v
