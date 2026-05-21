# Push the prepared branch to GitHub

The branch `add-intel-amd-comparison` is fully built inside the bundle file
in this folder. You only need to push it.

## Bundle contents

- `refs/heads/main`                        → `fb80d4d` (unchanged from remote)
- `refs/heads/add-intel-amd-comparison`    → `f786f74` (new commit, 27 files, +8409 lines)

## One-shot commands (run from any working directory)

```bash
# 1. Clone the repo fresh
git clone https://github.com/jhan-positron/notebook.git
cd notebook

# 2. Fetch the new branch from the bundle (adjust path to the .bundle file)
git fetch "<PATH-TO>/notebook-add-intel-amd-comparison.bundle" \
    add-intel-amd-comparison:add-intel-amd-comparison

# 3. Push it to GitHub
git push -u origin add-intel-amd-comparison
```

On Windows PowerShell the bundle path is:
`C:\Users\jibin\Downloads\files\intel-amd-comparison\_push\notebook-add-intel-amd-comparison.bundle`

## Open the PR

After the push succeeds, open this URL to create the PR (title and body
prefilled from the commit message):

https://github.com/jhan-positron/notebook/compare/main...add-intel-amd-comparison?expand=1
