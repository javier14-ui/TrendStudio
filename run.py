import sys
if __name__ == '__main__':
    if '--verify-install' in sys.argv:
        from trendstudio.diagnostics import main
    else:
        from trendstudio.app import main
    raise SystemExit(main())
