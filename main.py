"""Open the interactive virtual lab; use --batch for command-line experiments."""
import sys

if __name__ == '__main__':
    batch_options={'--batch','--benchmark','--config','--output-dir','--robustness','--robustness-only','--study-config'}
    if any(arg.split('=')[0] in batch_options for arg in sys.argv[1:]):
        if '--batch' in sys.argv: sys.argv.remove('--batch')
        from run_project import main
    else:
        from lab_server import main
    main()
