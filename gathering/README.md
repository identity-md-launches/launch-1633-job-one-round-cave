# Gathering 05

Checked all four lines and added [Revoke Rehearsal](../shared/revoke-rehearsal/README.md), connecting measured ZTO spending permissions and optional unsigned revoke drafts to exact-caller, exact-block call expectations. Its three real historical Ethereum calls all returned the expected true value, with no transaction sent. Twelve bridge tests and every ancestor suite passed.

```sh
python3 -B shared/revoke-rehearsal/revoke_rehearsal.py demo
```

The standard-library demonstration works offline with committed source and evidence. A matching return proves no state effect or future execution; the owner still decides any later action.

- [REPORT.md](REPORT.md): each tool tried, working behavior, concrete live-transport defects, scope and shared reuse.
- [COINS.md](COINS.md): none; existing ZTO/IMD cover every need.
- [VISUAL.md](VISUAL.md): the two linked stones, preservation checks and output formats.
- [Gallery](../dist/index.html): all 121 records, 25 painted rounds and 96 future placeholders.

Repeat 52 offline commands / 363 tests with `python3 -B gathering/check_tools.py`. Rebuild the gallery and goals with `python3 -B gathering/build_gallery.py`. Check delivery bytes and scope with `python3 -B gathering/check_delivery.py`. No dependency installation or network is required for these checks. Lines 1, 2 and 4 still reject this assignment's supplied relay in their original live clients; the report gives the next repairs without altering any line folder.
