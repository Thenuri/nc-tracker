# Demo run-through: a disputed cross-department NC, from logging to closure

About 10 minutes. It shows the SRS acceptance criteria working end to end
(Section 10), especially **#11: a pilot including a disputed cross-department NC**.

The same steps run automatically as a test: `python manage.py test ncs.test_demo`.

## Before you start

```bash
source .venv/bin/activate              # macOS  (Windows: .\.venv\Scripts\Activate.ps1)
python manage.py load_sample_data      # safe to run again
python manage.py runserver
```

Open http://127.0.0.1:8000/. To switch person, click the **initials circle** (top right)
and pick someone in **Who am I?**. Below, "**Who am I? → Nadia Demo**" means exactly that.
Emails appear in the terminal running `runserver`, and in the app under the **bell** (top right),
which shows a red number when there are unread ones.

| Person | Who am I? entry | Role |
| --- | --- | --- |
| Nadia Demo | NC Manager | Logs, decides disputes, verifies |
| Kasun Mock | Head of Department – IT | Raising department |
| Shalini Example | Head of Department – Finance | Receiving department |
| Arjun Sample | Action Owner – Finance | Does the corrective action |
| Leela Sample | Management | Read-only overview |

## The story

IT notices that online fee payments are not reconciled with the bank each week.
They tell the NC Manager. Finance thinks it isn't their job and disputes it.

### 1. Log the NC (NC Manager) – FR-01 to FR-08
1. **Who am I? → Nadia Demo.** Click the teal **+ Log an NC** button (top right).
2. Raising department **IT**, receiving department **Finance**, area **Fee collection**,
   source **Daily operations**, description *"Online fee payments are not reconciled
   with the bank statement each week."*, today's date, identified by *"IT Analyst Z. Sample"*.
3. Click **Log NC**. Note the new ID (e.g. **NC-2026-023**) and status **Pending validation**.
4. Point out: the terminal shows emails to the Finance HoD (with a link) and the IT HoD.

### 2. Everyone can see it, only Finance can validate – FR-13, FR-30
1. **Who am I? → Kasun Mock (IT).** Open **Register**, click the new NC.
2. Show "Nothing for you to do on this NC right now": IT raised it but cannot change it.

### 3. Finance disputes it – FR-09 to FR-11
1. **Who am I? → Shalini Example (Finance).** The NC is under **Waiting for you**.
2. Open it. In **Not valid? Dispute it**, try clicking **Mark as not valid** with no reason
   → it asks for one. Enter *"Reconciliation is IT's automated job, not Finance's."* and submit.
3. Status is now **Disputed**.

### 4. NC Manager decides – FR-12
1. **Who am I? → Nadia Demo.** Show the red number on the **bell**, then the NC under **Waiting for you**
   (it also has a yellow **Your action** tag in the **Register**).
2. **Decide the dispute → Overturn**, rationale *"Procedure FP-03 makes Finance responsible
   for reconciliation."* → status **Valid**.

### 5. Finance plans the fix – FR-16, FR-17, NFR-02
1. **Who am I? → Shalini Example.** Open the NC. **Assign Action Owner → Arjun Sample**.
2. **Who am I? → Arjun Sample.** Open the NC (it's in Waiting for you). In **Action plan**:
   root cause *"No one was named to do the weekly check."*, corrective action *"Name a
   reconciler and add a weekly checklist."*, a target date three weeks away → **In progress**.
   Only 4 fields.

### 6. Evidence and verification – FR-19, FR-21 to FR-23
1. Still Arjun: in **Action completed?** try **Send for verification** → refused until there is evidence.
2. **Add evidence**: *"Signed weekly checklist"* with a link (or upload a file). Then send for verification.
3. **Who am I? → Nadia Demo.** **Verify → Not effective**, comment *"Only one week shown.
   Please show four weeks."* → back to **In progress**.
4. **Who am I? → Arjun Sample.** The yellow box shows the NC Manager's comments.
   Add a progress note and more evidence, then send for verification again.
5. **Who am I? → Nadia Demo.** **Verify → Effective** → **Closed**. The page now offers only **Reopen**.

### 7. Oversight and audit – FR-24, FR-33 to FR-37, FR-42
1. Open **Change history** on the NC: every step, who did it and when.
2. Click **Printable record**: the full record from logging to closure for auditors.
3. **Who am I? → Leela Sample (Management).** Open **Dashboard**: tiles, charts, raised vs closed.
   Click the **Overdue** tile to jump to the filtered register.
4. In **Register**, click the **Closed** quick filter button, switch between **Cards** and **Table**,
   then **Export Excel**.

### Optional extras
- **Reminders:** run `python manage.py send_reminders --digest` in a second terminal,
  then look at Nadia's Notifications (overdue alerts, escalations, weekly digest).
- **Reopen:** as Nadia, reopen the closed NC with a reason; it appears in the history (FR-24).
- **No deletion (FR-43):** as Nadia, open the initials menu → **Manage lists** → **NCs → View**:
  there is no Delete button.
- **HoD nominee (FR-09):** **Who am I? → Priya Mock** (HoD nominee for Finance). She sees Finance's
  NCs in **Waiting for you** and can validate them while the HoD is away. The NC Manager sets
  nominees in **Manage lists → Departments**.
- **Public holidays (FR-14):** in **Manage lists → Public holidays**, add tomorrow as a holiday,
  then log an NC: the validation deadline moves one working day later.
- **Help (UI-06):** the **?** icon (top right) opens the one-page guide for HoDs and Action Owners,
  with **Print this guide**.
