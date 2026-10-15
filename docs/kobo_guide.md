# KoboToolbox guide: collecting field data on phones

For ARDE/KUBAHO staff who will set up and use **KoboToolbox**, a free tool widely used by NGOs for collecting data on
phones, even without internet. Field officers fill in the form on a phone, and the MEAL officer downloads the
results as an Excel file that this tool reads like the Excel templates.

> KoboToolbox is run by an outside organisation, not by this project. Screens, plan limits and server addresses can
> change: check the current details on https://www.kobotoolbox.org when setting up. Whether ARDE/KUBAHO may keep its
> data on KoboToolbox's servers (outside Rwanda) is a question under Law No. 058/2021: see
> `docs/privacy_and_governance.md` and `docs/partner_questions.md` (A5). **To be confirmed with ARDE/KUBAHO.**

## 1. What the forms are

Two forms are ready in the `forms/` folder of the project (built by `python src/build_kobo_forms.py` from the
programme master, so the dropdown lists match ARDE/KUBAHO's projects, activities, officers and villages):

| Form file | Replaces | One submission per |
|---|---|---|
| `forms/activity_monitoring_kobo.xlsx` | The activity monitoring Excel template | Activity (training, meeting, construction...) |
| `forms/indicator_report_kobo.xlsx` | The monthly indicator report | Indicator, project, district and month (women and men separately for indicators broken down by sex) |

The phone checks the answers as they are typed, so most of the problems the pipeline has to clean in Excel files
cannot happen: districts, sectors, cells and villages are chosen from lists (each list narrowed by the one before);
activities are filtered by project; dates cannot be in the future; numbers cannot be negative; and **the total must
equal women + men** before the form can be saved.

**Beneficiary registration is not on Kobo in this prototype** (it stays in the Excel register): a Kobo registration
form would put names, phone numbers and IDs on KoboToolbox's servers, which needs ARDE/KUBAHO's decision first.

## 2. Create a free account (MEAL officer, once, about 10 minutes)

1. Go to https://www.kobotoolbox.org and choose **Sign up**. Pick a server when asked: the **global** server, or the
   **European Union** server (the team suggests the EU one, because of its data-protection rules; to be decided by
   ARDE/KUBAHO). Remember which: the phones need the same server.
2. Register with an ARDE/KUBAHO email address (not a personal one), so the account stays with the organisation.
3. The free plan has monthly limits on submissions and storage: check that they are enough for the number of
   activities and reports per month.

## 3. Upload and publish the forms (MEAL officer, about 10 minutes)

1. Log in, click **New**, then **Upload an XLSForm**, and choose `forms/activity_monitoring_kobo.xlsx`. Give the
   project a name such as "ARDE activity monitoring".
2. Click **Deploy**. Kobo checks the form; it was checked with the same converter Kobo uses (pyxform), without errors.
3. Do the same for `forms/indicator_report_kobo.xlsx` ("ARDE indicator report").
4. Under **Settings > Sharing**, add the field officers' Kobo accounts (or one shared "data collector" account) with
   permission to **add submissions** only, so they cannot see or change other people's data.

When the programme master changes (a new project, activity or village), run `python src/build_kobo_forms.py` again,
then in Kobo open the project, **Replace** the form with the new file and **Redeploy**. Earlier submissions are kept.

## 4. Install KoboCollect on the phones (each field officer, about 15 minutes)

1. On an Android phone, install **KoboCollect** from the Google Play Store (free).
2. Open it and choose **Configure with QR code** (the MEAL officer can show the project's QR code from Kobo:
   **Form > Collect data**), or **Manually** enter the server address given on that page and the officer's username
   and password.
3. Tap **Download form** and select both ARDE forms.
4. To fill in a form: **Start new form**, answer the questions, then **Save form and exit**, marked as finalised.
   Forms can be filled **without internet**; tap **Send finalised form** when there is a connection.

Tips for officers: choose your own officer code; send forms at least weekly; if a form will not save, read the red
message (for example "The total must equal women + men") and correct the numbers.

## 5. Download the data for the dashboard (MEAL officer, each month)

1. In Kobo, open the project, then **Data > Downloads**.
2. Choose **XLS** as the export type. Under advanced options:
   - **Value and header format: XML values and headers** (recommended). "Labels" also works.
   - **Include groups in headers: off.**
   - Export all versions of the form.
3. Click **Export**, then download the file when it is ready.
4. Save it in the project's `data/raw/` folder **keeping "activity_monitoring" or "indicator_report" in the file
   name** (Kobo's own names do, for example `ARDE_activity_monitoring_-_all_versions_-_...xlsx`): the pipeline uses
   the name to know what the file holds.
5. Run the pipeline (`python src/pipeline.py`) and check the Data quality page as usual. Kobo exports and Excel files
   can be used side by side, for example while some officers still use Excel. **Do not keep an officer's Kobo export
   and an Excel file covering the same activities**, or they will be counted twice.

What the pipeline does with a Kobo export: it reads the questions by their names (or labels) through
`config/source_mappings.yaml`; it ignores Kobo's own columns (start, end, _id, _uuid, _submission_time...); it
removes a form submitted twice with exactly the same answers; and it leaves skipped optional answers blank.

## 6. If something goes wrong

| Problem | What to do |
|---|---|
| Kobo will not deploy the form | Rebuild it with `python src/build_kobo_forms.py` and upload the new file; note the message Kobo shows for the maintainer |
| The phone does not show the form | Check the server address and the account in KoboCollect; tap **Download form** again |
| The pipeline says SKIPPED for the export | The export was made with group names in the headers, or a new question was added: export again with "Include groups in headers" off, or add the new column name to `config/source_mappings.yaml` (maintenance guide, section 4) |
| A village or activity is missing from the list | Add it to the programme master, rebuild the forms, and replace the form in Kobo |
| The same activity appears twice | Two different submissions with different answers (for example different dates) are kept: delete the wrong one in Kobo (**Data > Table**) and export again |

## 7. How it was tested

The prototype was tested with synthetic Kobo exports made from the synthetic answer key (`src/generate_kobo_exports.py`),
in both export formats, including forms submitted twice and optional costs left blank. Results are in
`docs/phase2_cleaning_scorecard.md`, section "KoboToolbox exports". The forms were converted with pyxform 4.5.0 (the
converter KoboToolbox uses) without errors or warnings, but have **not yet been deployed on a real KoboToolbox
account or used on a phone**: that is the first step of the field test.
