# CatchDeal Amazon automation

This folder contains the first test version of the CatchDeal Amazon Creators API pipeline.

## Required GitHub Actions secrets

In **Repository → Settings → Secrets and variables → Actions**, create:

- `AMAZON_CLIENT_ID` — your Creators API Credential ID
- `AMAZON_CLIENT_SECRET` — your Creators API Credential Secret
- `AMAZON_CREDENTIAL_VERSION` — `3.2` for the credential shown in your Associates dashboard
- `AMAZON_PARTNER_TAG` — your Amazon India Associates partner tag

Never commit these values to the repository.

## Test

After adding the four secrets:

1. Open **Actions**.
2. Select **Update CatchDeal Amazon Products**.
3. Click **Run workflow**.
4. Wait for the job to finish.
5. The workflow generates `data/products.json` and commits it to the selected branch.

The first version uses six categories and three keyword searches per category, then keeps up to ten products per category. It requests product images, titles, offers and sales-rank resources from Amazon Creators API.

The workflow is intentionally **manual-only** for the first test. Once the catalogue is verified, we can enable a daily schedule.

Amazon's current Creators API documentation says Images/ItemInfo/DetailPageURL data should be cached for no more than one day, while Offers should be refreshed more frequently (one hour). This test therefore refreshes the complete catalogue daily when we enable the schedule.
