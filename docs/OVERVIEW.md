# NC Tracker – what the prototype does

*For review by the NC working group. Based on SRS v0.2. Prototype status: working end to end with sample data.*

## In one sentence

One shared web app where APIIT records every non-conformity (NC), the receiving department confirms and fixes it, the NC Manager checks the fix, and everyone who needs to can see where things stand.

It follows the SRS principle: **simple for departments, controlled by one owner, visible to everyone who needs to see it.**

---

## 1. How an NC moves through the system

```
NC Manager logs the NC
        │
        ▼
Pending validation ──► Receiving HoD: is it valid?
        │                    │
        │ Valid              │ Not valid (reason required)
        ▼                    ▼
      Valid             Disputed ──► NC Manager decides (rationale required)
        │                    ├─ Overturn → Valid
        │                    └─ Uphold  → Not Valid (kept on record, not counted as open)
        ▼
Action plan recorded (root cause, action, owner, target date)
        ▼
   In progress ──► evidence + completion date ──► Pending verification
        ▲                                               │
        │      Not effective (comments required)        │ NC Manager checks
        └───────────────────────────────────────────────┤
                                                        ▼ Effective
                                                     Closed (locked)
                                                        │
                                  NC Manager can reopen with a reason
```

- **Overdue** is a flag, not a status. An NC is overdue when its validation deadline or target date has passed and it is not Closed or Not Valid.
- Every step records **who** did it, **when**, and **why**, and notifies the right people.
- NCs can **never be deleted**. An invalid NC stays in the register marked "Not Valid".

---

## 2. Who can do what

| Action | NC Manager (+ delegate) | Receiving HoD | Action Owner | Other HoDs | Management | Other staff |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Log a new NC | ✔ | | | | | |
| See every NC in the institution | ✔ | ✔ read | | ✔ read | ✔ read | |
| See own department's NCs (raised or received) | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ read |
| Confirm valid / dispute | | ✔ | | | | |
| Decide a dispute | ✔ | | | | | |
| Assign the Action Owner | | ✔ | | | | |
| Record root cause, action, target date | | ✔ | ✔ | | | |
| Add progress notes and evidence | | ✔ | ✔ | | | |
| Change target date (reason required) | | ✔ | ✔ | | | |
| Send for verification | | ✔ | ✔ | | | |
| Verify and close / send back | ✔ | | | | | |
| Reopen a closed NC | ✔ | | | | | |
| Dashboard and exports | ✔ | ✔ | ✔ own dept | ✔ | ✔ | ✔ own dept |
| Manage lists (departments, processes, sources, public holidays) | ✔ | | | | | |

People only see the buttons for what they are allowed to do. If someone tries a direct link to an action they may not take, the system refuses it.

The **raising department** can follow its NC but cannot change it.

Each department can also have an optional **HoD nominee** (set by the NC Manager in the admin). The nominee can do everything the receiving HoD can on their department's NCs, and gets the same notifications, so NCs keep moving when the HoD is away (FR-09).

---

## 3. The screens

### My tasks (start page)
A list of NCs **waiting for you**, oldest first:
- **NC Manager:** disputes to decide, NCs waiting for verification
- **HoD:** new NCs to validate, valid NCs needing an action plan
- **Action Owner:** NCs in progress assigned to them

### Log an NC (NC Manager only)
All the Part A fields from the SRS on one page:
- raising and receiving department
- area / process and source (with "Other" + description)
- description and date identified (no future dates)
- identified by
- optional severity and attachment

The system then:
- gives the NC an ID such as **NC-2026-023** (numbering restarts every year)
- sets the validation deadline to **3 working days** later (Mon–Fri, skipping the public holidays the NC Manager has entered)
- notifies the receiving HoD and the raising department's HoD

### NC page
Everything about one NC on one page:
- the NC details (Part A)
- validation or dispute, and the NC Manager's decision with rationale
- the action plan, showing the original target date if it was changed
- completion and verification, with "not effective" comments shown clearly to the owner
- evidence (files or links), progress notes and target-date changes
- the **full change history**: who did what, and when
- a **"What you can do"** panel showing only the actions this person can take now
- a **Printable record** button: the full record from logging to closure, for auditors

### Register
The central list of all NCs the person may see, as **cards** (default) or a compact **table**.
- **Quick filters** with counts: All, Open, Overdue, and each status, one click each.
- **Search** box and **sort** (newest, oldest, most urgent first) always visible.
- **More filters:** receiving department, raising department, area/process, source, Action Owner, and date identified from/to.
- **"Your action"** tag on NCs waiting for the person looking at the list.
- **Colour coding:** red = overdue, amber = due within 7 days, green = on track or closed.
- **Export:** Excel or PDF of exactly what is on screen.

### Dashboard
- **Counts:** open, overdue, pending validation, disputed, valid, in progress, pending verification, closed, not valid, total, and average days to close. Click a count to open those NCs in the register.
- **Charts:** NCs by receiving department, by raising department, by process and by source; raised vs closed per month (last 12 months); time taken to close.
- Each chart can also be shown as a table.
- HoDs and Management see the whole institution. Other staff see their own department.

### Notifications
Every message sent to a person. The **bell** in the top bar shows the unread count. Clicking one opens the NC.

### Help
A one-page guide (the **?** in the top bar, and **Help** in the footer): how to report a problem to the
NC Manager, step-by-step instructions for HoDs, nominees and Action Owners, and what each status means.
It can be printed.

### Manage lists (NC Manager)
Cards for each list: departments (with HoD and nominee), areas/processes, sources and **public holidays**,
with counts, plus view-only NC records and notifications. Lists are switched off ("Active"), never deleted;
holidays can be deleted.

---

## 4. Automatic notifications and reminders

**When something happens:**

| When | Who is told |
|---|---|
| NC logged | Receiving HoD (with a direct link) and raising department HoD |
| NC disputed | NC Manager and delegate |
| Dispute decided | Receiving HoD and raising HoD |
| Action Owner assigned | The Action Owner |
| Sent for verification | NC Manager and delegate |
| Closed, not effective, or reopened | Receiving HoD and Action Owner |

**Daily check (runs automatically once a day):**

| Rule | Who is told |
|---|---|
| Validation deadline is today | Receiving HoD |
| Validation deadline missed | Receiving HoD + NC Manager |
| Target date is 7 days away | Action Owner |
| Target date passed | Receiving HoD + Action Owner |
| 14 days past target date | NC Manager (escalation) |
| Every Monday | NC Manager: summary of open and overdue NCs |

Each reminder is sent only once. If the target date is moved, the reminders start again for the new date.

---

## 5. Records, audit and reports

| Need (SRS Section 9) | How the system covers it |
|---|---|
| Open, overdue and pending-validation list | Register filters, or the Monday summary |
| Summary by department and process | Dashboard charts |
| Cross-department summary (raised vs received) | Dashboard: "by raising" and "by receiving" charts |
| Closure ageing and effectiveness | Dashboard: average days to close, time-to-close chart |
| Full register export with evidence links | Register → Export Excel |
| Individual NC record, identification to closure | NC page → Printable record |

- **Audit trail:** every change is recorded with who, what and when.
- **No deletion:** NCs cannot be deleted by anyone, including in the admin screens.
- **Closed NCs are locked:** only the NC Manager can reopen them, and a reason is required.
- **Private files:** attachments and evidence can only be opened by people allowed to see that NC.

---

## 6. Decisions we made for the [TBC] items (please confirm)

These are **settings**, so they can be changed later without any programming.

| Open question in the SRS | What the prototype does now |
|---|---|
| Validation deadline | **3 working days** (Mon–Fri, skipping public holidays entered in Manage lists) |
| Reminder before target date | **7 days** before |
| Escalation to NC Manager | **14 days** overdue |
| Same-department NCs | **Still need validation** (can be switched to automatic) |
| Severity (Minor / Major) | **Optional** field |
| NC ID format | **NC-YYYY-###**, restarting each year |
| Who can see NC content in other departments | **All HoDs see full details**, read-only |
| Management view | **Same as HoDs:** everything, read-only |
| Raising department | **Can view its NCs**, cannot change them or comment |
| Disputes the NC Manager can't settle | **Not built yet:** the NC Manager records the final decision |

---

## 7. Prototype vs. the real system

The prototype works end to end. Three parts are temporary until APIIT IT provides the real ones:

| In the prototype | In the real system |
|---|---|
| "Who am I?" picker to switch between sample people | Sign in with APIIT Microsoft (apiit.lk) accounts |
| Notifications shown on screen; emails printed on the laptop | Real emails from **nctracker@apiit.lk** |
| Runs on a laptop with sample data and a yellow "PROTOTYPE" banner | Runs on the APIIT server with real data, no banner |

The PDF export currently opens a print-ready page ("Save as PDF") on Windows laptops. It produces PDF files directly on the server.

---

## 8. Try it yourself (about 10 minutes)

Ask the developer to start the prototype, then follow **docs/DEMO.md**. It takes one NC through the whole process:

1. **NC Manager (Nadia Demo)** logs an NC raised by IT against Finance.
2. **IT HoD (Kasun Mock)** can see it but cannot change it.
3. **Finance HoD (Shalini Example)** disputes it with a reason.
4. **NC Manager** overturns the dispute with a rationale.
5. **Finance HoD** assigns **Action Owner (Arjun Sample)**, who records the plan.
6. Arjun adds evidence and sends it for verification.
7. **NC Manager** marks it "not effective". Arjun sees the comments, adds more evidence and sends it again.
8. **NC Manager** closes it. **Management (Leela Sample)** reviews the dashboard, register and printable record.

All names are fake sample people.

---

## 9. Questions for the team

1. Does the step-by-step process (Section 1) match how you expect NCs to be handled?
2. Are the roles and permissions in Section 2 right? Should anyone see more or less?
3. Are the defaults in Section 6 acceptable (3 / 7 / 14 days, same-department validation, severity optional)?
4. Should the raising department be able to **add comments** on an NC it raised?
5. Who should resolve a dispute the NC Manager cannot settle, and should the system record that step?
6. Is the action plan short enough (root cause, corrective action, owner, target date, plus evidence)?
7. Are any reports or dashboard figures missing?
8. Public holidays are now skipped in the 3-working-day deadline: who will enter each year's holiday list?
9. Who will be the named NC Manager and delegate?
