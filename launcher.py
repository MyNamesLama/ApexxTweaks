from tweaker.gui import main
if __name__ == '__main__':
    import sys
    raise SystemExit(main(smoke='--smoke-test' in sys.argv))
