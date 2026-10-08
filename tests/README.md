**Verification**

Run the Python physics, configuration and HTTP workflow tests from the project folder:

```bash
python -m unittest discover -s tests -v
```

The HTTP tests start their own local test server and run all three objects.

The optional JavaScript controller check uses Node.js and jsdom. These are
**test-only dependencies**, not needed to use the lab. With jsdom installed
in your development environment and `python lab_server.py --no-browser`
running on port 8765, run:

```bash
node tests/ui_controller.cjs
```

It checks controls and real API calls using a simulated DOM with canvas drawing
stubbed. It does not verify pixels, fonts or visual layout in a live browser.
See outputs/test_results.txt and outputs/ui_controller_test.txt for recorded results.
