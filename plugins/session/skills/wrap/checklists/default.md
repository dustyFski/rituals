# Default wrap checklist

Answer each item PASS, FAIL, or N-A, with one line of evidence. A project overrides this
file with `.claude/wrap-checklist.md`.

## BLOCKER

1. **Secrets:** does the session change set contain an API key, token, password, or private
   key? Scan staged, unstaged, untracked, and this session's commits, not `git diff` alone.
   Evidence: a key-shape grep over that whole set, including `git log -p -m <baseline>..HEAD`.
   The endpoint diff alone misses a key that was committed and then reverted in the same
   session. A hit means rotate the key, because deleting it does not clear git history.
2. **Outbound scope:** if the session touched code that sends, publishes, or writes to an
   external system, is the destination authorized and in scope for this session?
   Evidence: the line naming the channel, ID, or URL. An unfiltered recipient loop fails.
3. **Destructive commands:** does anything added this session delete, reset, or overwrite
   data without a guard? Evidence: the guard line, or the absence of such a command.
4. **Credentials in tracked files:** is every credential read from the environment or a
   secret store rather than a literal? Evidence: the env lookup line.

## WARNING

5. **Tests:** does the test suite pass on the current tree?
   Evidence: the runner command and its exit status. No suite is N-A, not PASS.
6. **New logic has a check:** does every non-trivial function added this session have one
   runnable check that was run and fails when the logic breaks?
   Evidence: name the run, its command, and its result.
7. **Broken paths:** does every input file path and link added this session resolve?
   Generated outputs are excluded. Evidence: the resolve command output.
8. **Stale references:** does anything still reference a file, flag, or name removed this
   session? Evidence: a grep for the old name returning nothing.
9. **Cross-file agreement:** if a fact appears in two files, do they match?
   Evidence: both lines quoted side by side.
10. **Unverified numbers:** is every externally presented factual claim with a number traced
    to a source, or labelled an estimate? Evidence: the source URL or the estimate label.
11. **Uncommitted work:** does `git status` show generated output that nothing will keep?
    Evidence: the status output. Report it; do not commit it unasked.
12. **Error paths:** does new code that can fail report the real error rather than swallow
    it? Evidence: the raise, log, or return line.

## HOUSEKEEPING

13. **Docs match behavior:** does the README still describe what the code now does?
    Evidence: the changed line, or a note that nothing user-facing moved.
14. **Naming consistency:** do new files follow the naming convention already in the
    directory? Evidence: a listing of the sibling files.
15. **Dead code:** did this session leave a function, flag, or branch nothing calls?
    Evidence: a caller search returning zero hits.
16. **Config drift:** does every new config value have a default, or is it documented as
    required? Each needs a documented meaning. Evidence: the default or the required note.
