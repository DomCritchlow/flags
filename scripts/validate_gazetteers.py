"""Validate all gazetteer files for conflicts, missing data, and consistency."""

import sys
from pipeline.gazetteer import Gazetteer, GazetteerValidationError


def main():
    print("Loading gazetteers...")
    try:
        g = Gazetteer()
    except GazetteerValidationError as e:
        print(f"FATAL: {e}")
        sys.exit(1)

    print(f"\nStats:")
    for key, val in g.stats().items():
        print(f"  {key}: {val}")

    print(f"\nRunning validation...")
    issues = g.validate()

    if issues:
        print(f"\nFound {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\nAll validations passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
