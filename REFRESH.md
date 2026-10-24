# CatchDeal publishing

The website and collectors run together in **Refresh CatchDeal and deploy**.
There is no `WEBSITE_REPO_TOKEN` dependency and no cross-repository checkout.
GitHub supplies a short-lived `GITHUB_TOKEN` automatically for each job.

- Automatic refresh: Mondays at 03:20 UTC / 07:20 Dubai.
- Manual refresh: Actions → Refresh CatchDeal and deploy → Run workflow.
- To republish the checked-in catalogue without contacting Amazon, uncheck
  **Collect fresh Amazon products before publishing** on the manual run form.
- Pushes that change code also collect and deploy; data-only bot commits do not
  start another run.
- Both collectors write into staging. Validation checks required fields, affiliate
  links, Amazon image hosts, unique ASINs, search coverage, and generation dates.
  A refresh losing more than 20% of products or search terms is rejected.
- A failed collection, validation, or build does not replace the deployed site.
- Only HTML, CSS, JavaScript, assets, data and CNAME are packaged for Pages.
- Pages source should be **GitHub Actions** in Settings → Pages. The custom
  `catchdeal.in` domain remains attached to the same repository.
- Failure details appear in the Actions run. GitHub's personal Actions notification
  settings control failure emails; they are not changed by this workflow.

The former private collector repository is retained for history. Its old workflow
is disabled after the new refresh and recovery deployments were verified. Update the scripts here for future changes.

The optional voice/shortcut endpoint in `catchdeal-refresh-trigger` dispatches
`refresh-and-deploy.yml` in this repository. Its separate `GITHUB_TRIGGER_TOKEN`
needs Actions write access here; the scheduled refresh and Pages deployment do
not use that credential.
