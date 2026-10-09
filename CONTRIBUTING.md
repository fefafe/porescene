# Contributing

## A note up front

PoreScene is developed by a process engineer, not a professional software developer. It
grew out of the need for reproducible, publication-quality figures in porous media
research, and the code reflects that: it is written to get the job done and improved
along the way. You will likely find rough edges – inconsistent interfaces, gaps in the
tests, Blender quirks that are worked around rather than solved, or documentation that
lags behind the code.

If you spot something that could be done better, please say so. Suggestions, bug
reports, and pull requests are all welcome.

## Reporting issues

Open an issue on [GitHub](https://github.com/fefafe/porescene/issues) and include:

- the PoreScene and Python versions, and your operating system,
- a minimal script that reproduces the problem,
- what you expected and what happened instead (rendered images help).

## Pull requests

1. Fork the repository and create a branch from `main`.
2. Set up the development environment:

   ```console
   poetry install
   pre-commit install
   ```

3. Make your changes and keep them focused on a single topic.
4. Run the tests with `pytest` and make sure the pre-commit hooks pass.
5. Open a pull request describing what you changed and why.

## Examples

Scripts in `example/` read their input only from `data/` and write all output to
`tmp/example/<script name>/`, which git ignores. `data/` holds nothing but the datasets
the examples take as input. A new example should start from the paths block of an
existing one.
