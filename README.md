# pagerduty_takeaway


This is a simple Python script that uses PagerDuty's API to extract relevant information for migrating the customer over to  VictorOps.  Depending on the "abilities" associated with the customer's PD account (their pricing tier and features etc.), this script will pull out their users and team information and write the data to .csv files that are formatted for upload to VictorOps using our internal onboarding tool.

### System requirements
* python3 - required modules = requests, csv

### Other requirements
* The customer's PagerDuty API athentication token.
