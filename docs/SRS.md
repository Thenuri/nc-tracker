**Software Requirements Specification**

Institutional Non-Conformity (NC) Recording & Tracking Mechanism

| **Document version** | **0.2 (Draft for review)**                        |
|----------------------|---------------------------------------------------|
| **Prepared by**      | Fathima (Lead), with Nirushan, Shyrah, Kanishka   |
| **Prepared for**     | Management (requester)                            |
| **Purpose**          | Preparation for Stage 2 External Audit            |
| **Target go-live**   | 1 October 2026                                    |
| **Status**           | Draft. Items marked **\[TBC\]** need confirmation |

**Changes in v0.2:** NC logging is restricted to the NC Manager; HoDs
can monitor all NCs institution-wide; the receiving department validates
each NC; cross-department NCs are supported. See Section 14.

# 1. Introduction

## 1.1 Purpose

This document specifies the requirements for a simple, consistent
mechanism to record, validate, follow up and close non-conformities
(NCs) arising from day-to-day operations, with a single institution-wide
view of their status.

## 1.2 Scope

**In scope**

- NCs identified through daily departmental activities, processes,
  internal reviews, monitoring and similar routine checks, including NCs
  one department identifies in another.

- Central register, validation by the receiving department, corrective
  action tracking, evidence, verification and closure, reminders, and
  reporting.

**Out of scope**

- Recording of **audit findings** as a formal audit-reporting process.

- Risk management, incident investigation and document control
  workflows.

- Any feature that adds significant administrative burden to
  departments.

## 1.3 Guiding principle

> *Simple for departments, controlled by one owner, visible to everyone
> who needs to see it.*

Departments do not need to learn a system to report an NC. They tell the
NC Manager, who logs it. The receiving department's main job is to
confirm validity and act.

## 1.4 Definitions

| **Term**               | **Meaning**                                                                                                             |
|------------------------|-------------------------------------------------------------------------------------------------------------------------|
| NC                     | Non-conformity: failure to fulfil a requirement (policy, procedure, standard, regulation or stakeholder requirement)    |
| NC Manager             | The single designated person (or small named team) authorised to log NCs and verify closure **\[TBC: name\]**           |
| Raising department     | The department that identified the NC (may be the same as the receiving department)                                     |
| Receiving department   | The department the NC is raised against and which must validate and correct it                                          |
| HoD                    | Head of Department **\[TBC: confirm whether "HoD" includes Heads of all departments only, or also senior management\]** |
| Action Owner           | Person in the receiving department responsible for the corrective action                                                |
| Validation             | The receiving department's decision on whether the NC is valid                                                          |
| Register               | The central list of all NCs                                                                                             |
| Corrective action (CA) | Action taken to eliminate the cause and prevent recurrence                                                              |

## 1.5 Source

Requirements derive from the management brief to the working group
(Fathima, Nirushan, Shyrah, Kanishka) and from follow-up clarifications
on roles and cross-department handling. Section 12 traces requirements
to the brief.

# 2. Overall Description

## 2.1 Product perspective

A lightweight, standalone solution consisting of:

1.  **An NC entry form**, used only by the NC Manager (and a delegate)
    to log NCs.

2.  **A central register** holding every NC, with a single source of
    truth.

3.  **A receiving-department view**, where the HoD or nominee validates
    the NC and records the root cause and corrective action.

4.  **A monitoring dashboard**, open to all HoDs (read-only) and
    Management.

5.  **Automated notifications** and reminders.

## 2.2 Recommended implementation approach

|                             | **Option A: Form + shared list/database (recommended)**                                          | **Option B: Shared spreadsheet tracker (interim fallback)** |
|-----------------------------|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| Example stack               | Microsoft Forms/Power Apps + SharePoint List + Power Automate + Power BI (or Google equivalents) | One protected Excel / Google Sheet                          |
| Role-based access           | Strong: only the NC Manager can add; departments update only their own NCs                       | Weak: sheet-level permissions only                          |
| Central visibility for HoDs | Live dashboard                                                                                   | Manual                                                      |
| Reminders and escalation    | Automated                                                                                        | Manual or scripted                                          |
| Audit trail                 | Built in                                                                                         | Limited                                                     |
| Setup before 1 Oct          | Low to medium                                                                                    | Low                                                         |

Because only one person logs NCs, the entry form can be simple and
internal. Departments interact with the system only when validating and
updating their own NCs.

**Decision needed:** confirm platform (Microsoft 365 or Google
Workspace) and administrator.

## 2.3 User classes

| **User**                     | **Description**                                                            | **Typical actions**                                                                           |
|------------------------------|----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| **NC Manager**               | Only user who logs NCs. Also verifies closure and administers the register | Log NC, assign receiving department, resolve disputes, verify and close, report, manage lists |
| **Receiving department HoD** | Head of the department the NC is raised against                            | Validate or dispute NC, assign Action Owner, oversee actions                                  |
| **Action Owner**             | Person nominated by the receiving HoD                                      | Record root cause and corrective action, upload evidence, update status                       |
| **HoDs (all departments)**   | Head of any department                                                     | **Monitor all NCs across the institution (read-only)**; act on their own department's NCs     |
| **Management**               | Oversight                                                                  | Read-only access to everything, dashboard and reports                                         |
| **Raising department**       | Department that identified a cross-department NC                           | Informs the NC Manager; can view the NC they raised; may be asked for clarification           |

## 2.4 Operating environment

Web browser on desktop and mobile; institutional login; no local
installation.

## 2.5 Constraints

- No significant additional administrative burden on departments.

- Existing institutional licences only, unless approved.

- The NC Manager is a single point of entry, so continuity is required
  (a named delegate **\[TBC\]**).

## 2.6 Assumptions

- Departments report NCs to the NC Manager through an agreed simple
  channel (email, message or in person), with the information needed in
  Section 4.1.

- Every department has a HoD who can validate NCs raised against it.

- The NC Manager has capacity to log and verify NCs at the expected
  volume.

# 3. Process Overview

**Status transitions**

| **From**             | **To**               | **Trigger**                                              |
|----------------------|----------------------|----------------------------------------------------------|
| (start)              | Pending Validation   | NC Manager logs NC and notifies the receiving department |
| Pending Validation   | Valid                | Receiving department confirms valid                      |
| Pending Validation   | Disputed             | Receiving department marks not valid (reason required)   |
| Disputed             | Valid                | NC Manager overturns the dispute                         |
| Disputed             | Not Valid            | NC Manager upholds the dispute                           |
| Valid                | In Progress          | Root cause, action, owner and target date recorded       |
| In Progress          | Pending Verification | Action completed and evidence attached                   |
| Pending Verification | Closed               | NC Manager verifies as effective                         |
| Pending Verification | In Progress          | Not effective; rework required                           |

**Statuses**

| **Status**               | **Meaning**                                                                      |
|--------------------------|----------------------------------------------------------------------------------|
| Pending Validation       | Logged and sent to the receiving department; awaiting valid / not valid decision |
| Valid                    | Confirmed as a valid NC; awaiting action plan                                    |
| Disputed                 | Receiving department states it is not valid; NC Manager decides                  |
| In Progress              | Root cause and corrective action recorded; action under way                      |
| Pending Verification     | Action completed with evidence; awaiting NC Manager verification                 |
| Closed                   | Verified as effective                                                            |
| Not Valid                | Dispute upheld; record retained with reason, excluded from open NC counts        |
| *Overdue* (derived flag) | Validation deadline or target date passed, and the NC is not Closed or Not Valid |

## 3.1 Cross-department handling

- The NC Manager records both the **raising department** and the
  **receiving department**.

- The receiving department validates the NC. The raising department
  cannot close or change it.

- If the receiving department disputes the NC, the NC Manager reviews it
  with both parties and decides. If unresolved, it goes to Management
  **\[TBC\]**.

- NCs within a single department are logged with the same department as
  raising and receiving; validation still applies **\[TBC: or
  auto-validate\]**.

# 4. Data Requirements

## 4.1 Part A: Logging (completed by NC Manager)

| **\#** | **Field**                         | **Type**             | **Required** | **Notes**                                                                      |
|--------|-----------------------------------|----------------------|--------------|--------------------------------------------------------------------------------|
| A1     | NC ID                             | Auto                 | Auto         | Format NC-YYYY-###                                                             |
| A2     | Raising department                | Dropdown             | Yes          | Controlled list                                                                |
| A3     | Receiving department              | Dropdown             | Yes          | Controlled list                                                                |
| A4     | Area / Process                    | Dropdown (+ "Other") | Yes          |                                                                                |
| A5     | Description of the non-conformity | Long text            | Yes          | What happened and which requirement was not met                                |
| A6     | Date identified                   | Date                 | Yes          | Not a future date                                                              |
| A7     | Source of identification          | Dropdown             | Yes          | Daily operations, Internal review, Monitoring/KPI, Stakeholder feedback, Other |
| A8     | Identified by (person)            | Text                 | Yes          | Person who found it in the raising department                                  |
| A9     | Logged by / date logged           | Auto                 | Auto         |                                                                                |
| A10    | Supporting attachment             | File                 | No           | Photo, record or email                                                         |
| A11    | Severity (optional)               | Dropdown             | No           | Minor / Major, if QMS defines it **\[TBC\]**                                   |

## 4.2 Part B: Validation (Receiving HoD or nominee)

| **\#** | **Field**             | **Type**          | **Required**     |
|--------|-----------------------|-------------------|------------------|
| B1     | Validation decision   | Valid / Not valid | Yes              |
| B2     | Reason (if not valid) | Text              | Yes if not valid |
| B3     | Validated by / date   | Auto              | Auto             |

## 4.3 Part C: Action planning (Receiving department)

| **\#** | **Field**                         | **Type**      | **Required** |
|--------|-----------------------------------|---------------|--------------|
| C1     | Root cause                        | Long text     | Yes          |
| C2     | Corrective action                 | Long text     | Yes          |
| C3     | Responsible person (Action Owner) | Person picker | Yes          |
| C4     | Target completion date            | Date          | Yes          |

## 4.4 Part D: Completion and closure

| **\#** | **Field**                      | **Type**                      | **Required**                    |
|--------|--------------------------------|-------------------------------|---------------------------------|
| D1     | Status                         | Dropdown / auto               | Yes                             |
| D2     | Date action completed          | Date                          | Yes before Pending Verification |
| D3     | Evidence of completion         | File or link with description | Yes before Pending Verification |
| D4     | Verification outcome           | Effective / Not effective     | Yes (NC Manager)                |
| D5     | Verification comments          | Text                          | Yes if not effective            |
| D6     | Verified by / date             | Auto                          | Auto                            |
| D7     | Closure date                   | Auto                          | Auto                            |
| D8     | Dispute decision and rationale | Text                          | Yes if disputed (NC Manager)    |

## 4.5 System fields

Created and last modified date/by, days open, overdue flag, and full
change history.

# 5. Functional Requirements

Priority: **M** = Must (1 Oct go-live), **S** = Should, **C** = Could.

## 5.1 Logging NCs

| **ID** | **Requirement**                                                                     | **Priority** |
|--------|-------------------------------------------------------------------------------------|--------------|
| FR-01  | Only the NC Manager (and named delegate) shall be able to create an NC              | M            |
| FR-02  | The system shall provide a single entry form capturing Part A fields                | M            |
| FR-03  | The system shall auto-generate a unique NC ID                                       | M            |
| FR-04  | The system shall require both raising and receiving departments                     | M            |
| FR-05  | The system shall enforce required fields, valid dates and controlled dropdown lists | M            |
| FR-06  | The system shall support attachments at logging                                     | S            |
| FR-07  | The system shall notify the raising department that its NC has been logged          | S            |

## 5.2 Validation by receiving department

| **ID** | **Requirement**                                                                                                       | **Priority** |
|--------|-----------------------------------------------------------------------------------------------------------------------|--------------|
| FR-08  | On logging, the system shall notify the receiving HoD and give a link to the NC                                       | M            |
| FR-09  | The receiving HoD (or nominee) shall be able to mark the NC Valid or Not valid                                        | M            |
| FR-10  | A reason shall be mandatory for Not valid                                                                             | M            |
| FR-11  | A Not valid decision shall set status to Disputed and notify the NC Manager                                           | M            |
| FR-12  | The NC Manager shall be able to uphold (Not Valid) or overturn (Valid) a dispute, with rationale recorded             | M            |
| FR-13  | Only the receiving department may validate its NCs; the raising department cannot                                     | M            |
| FR-14  | A validation deadline (default 3 working days **\[TBC\]**) shall apply, with reminders and NC Manager alert if missed | S            |
| FR-15  | Not Valid NCs shall remain in the register with reason, excluded from open counts                                     | M            |

## 5.3 Action planning and follow-up

| **ID** | **Requirement**                                                                                         | **Priority** |
|--------|---------------------------------------------------------------------------------------------------------|--------------|
| FR-16  | The receiving HoD shall assign an Action Owner and the Action Owner shall be notified                   | M            |
| FR-17  | The receiving department shall record root cause, corrective action, responsible person and target date | M            |
| FR-18  | Receiving department users shall be able to update status and add progress notes on their own NCs only  | M            |
| FR-19  | The system shall prevent Pending Verification without completion date and evidence                      | M            |
| FR-20  | Target date changes shall require a reason and preserve the original date                               | S            |

## 5.4 Verification and closure

| **ID** | **Requirement**                                                                   | **Priority** |
|--------|-----------------------------------------------------------------------------------|--------------|
| FR-21  | Only the NC Manager shall be able to verify and close an NC                       | M            |
| FR-22  | The verifier shall record outcome (effective / not effective) and comments        | M            |
| FR-23  | Not effective NCs shall return to In Progress, with comments visible to the owner | M            |
| FR-24  | Closed NCs shall be locked; only the NC Manager may reopen, with audit trail      | S            |

## 5.5 Reminders and escalation

| **ID** | **Requirement**                                                                                                            | **Priority** |
|--------|----------------------------------------------------------------------------------------------------------------------------|--------------|
| FR-25  | The system shall flag NCs as Overdue automatically (validation or target date passed)                                      | M            |
| FR-26  | Action Owner shall be reminded before the target date (7 days **\[TBC\]**)                                                 | S            |
| FR-27  | Receiving HoD shall be notified of overdue NCs; the NC Manager shall be notified of NCs overdue beyond 14 days **\[TBC\]** | S            |
| FR-28  | The NC Manager shall receive a weekly digest of open and overdue NCs                                                       | C            |

## 5.6 Central register, monitoring and reporting

| **ID** | **Requirement**                                                                                                                          | **Priority** |
|--------|------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| FR-29  | The system shall maintain one central register of all NCs for all departments                                                            | M            |
| FR-30  | **All HoDs shall have read-only access to every NC in the register, across all departments**                                             | M            |
| FR-31  | Management shall have read-only access to all NCs and the dashboard                                                                      | M            |
| FR-32  | The register shall be filterable by raising department, receiving department, area/process, status, source, owner, date and overdue flag | M            |
| FR-33  | The dashboard shall show totals, pending validation, disputed, in progress, pending verification, closed and overdue                     | M            |
| FR-34  | The dashboard shall show NCs by receiving department, by raising department, by process and by source                                    | M            |
| FR-35  | The dashboard shall show closure ageing, average days to close and monthly raised vs closed trend                                        | S            |
| FR-36  | The register and filtered views shall be exportable to Excel/PDF                                                                         | M            |
| FR-37  | A printable per-NC record from logging to closure shall be available                                                                     | S            |
| FR-38  | Recurrence view: repeated NCs by receiving department and process                                                                        | C            |

## 5.7 Access and administration

| **ID** | **Requirement**                                                                                  | **Priority** |
|--------|--------------------------------------------------------------------------------------------------|--------------|
| FR-39  | Access shall be via institutional login with role-based permissions (Section 6)                  | M            |
| FR-40  | HoDs shall be able to edit only NCs where their department is the receiving department           | M            |
| FR-41  | The NC Manager shall maintain lists (departments, HoDs, processes, sources) without code changes | M            |
| FR-42  | The system shall keep an audit trail of all changes (who, what, when)                            | M            |
| FR-43  | NCs shall not be deletable by any user; invalid NCs are recorded as Not Valid                    | M            |

# 6. Access Matrix

| **Action**                                | **NC Manager** | **Receiving HoD** | **Action Owner** | **Other HoDs** | **Management** |
|-------------------------------------------|----------------|-------------------|------------------|----------------|----------------|
| Log NC                                    | ✔              |                   |                  |                |                |
| View all NCs (institution-wide)           | ✔              | ✔ (read)          | Own dept         | ✔ (read)       | ✔ (read)       |
| Validate / dispute NC                     |                | ✔                 |                  |                |                |
| Decide on dispute                         | ✔              |                   |                  |                |                |
| Assign Action Owner                       |                | ✔                 |                  |                |                |
| Enter root cause, action, dates, evidence |                | ✔                 | ✔                |                |                |
| Update status up to Pending Verification  |                | ✔                 | ✔                |                |                |
| Verify and close                          | ✔              |                   |                  |                |                |
| Reopen closed NC                          | ✔              |                   |                  |                |                |
| Dashboard and export                      | ✔              | ✔                 | Dept view        | ✔              | ✔              |
| Manage lists and settings                 | ✔              |                   |                  |                |                |

# 7. User Interface Requirements

- **UI-01** NC Manager entry screen with all Part A fields on one page.

- **UI-02** Receiving department page pre-filled with NC details; users
  complete only the fields relevant to their stage (validate, then
  action, then evidence).

- **UI-03** The email notification to the receiving HoD contains a
  direct link, with a one-click Valid / Not valid choice.

- **UI-04** HoD monitoring dashboard on one screen with colour-coded
  status (red overdue, amber due within 7 days, green on track or
  closed).

- **UI-05** Plain language labels and mobile-friendly layout.

- **UI-06** A one-page guide for HoDs and Action Owners, plus a short
  briefing for departments on how to report an NC to the NC Manager.

# 8. Non-Functional Requirements

| **ID** | **Category**    | **Requirement**                                                                          |
|--------|-----------------|------------------------------------------------------------------------------------------|
| NFR-01 | Usability       | A receiving department user can validate and update an NC after reading a one-page guide |
| NFR-02 | Simplicity      | Receiving department completes no more than 4 action-planning fields plus evidence       |
| NFR-03 | Availability    | Available during working hours, 99% uptime per platform SLA                              |
| NFR-04 | Performance     | Submissions and dashboard refresh within 5 seconds                                       |
| NFR-05 | Security        | Institutional login, role-based access, data held in the institution's tenant            |
| NFR-06 | Integrity       | Full audit trail; no deletion of records                                                 |
| NFR-07 | Retention       | Records kept for the QMS retention period **\[TBC\]**                                    |
| NFR-08 | Continuity      | A named NC Manager delegate has equivalent rights                                        |
| NFR-09 | Maintainability | Lists and rules changeable without a developer                                           |
| NFR-10 | Scalability     | At least 1,000 NCs per year                                                              |
| NFR-11 | Privacy         | Only names and work emails needed for the process are stored                             |

# 9. Reporting Outputs

| **Report**                                       | **Frequency** | **Audience**     |
|--------------------------------------------------|---------------|------------------|
| Open, overdue and pending-validation NC list     | Weekly        | NC Manager, HoDs |
| NC summary by receiving department and process   | Monthly       | HoDs, Management |
| Cross-department NC summary (raised vs received) | Monthly       | HoDs, Management |
| Closure ageing and effectiveness                 | Monthly       | Management       |
| Full register export with evidence links         | On demand     | Auditors         |
| Individual NC record, identification to closure  | On demand     | Auditors         |

# 10. Acceptance Criteria

1.  Only the NC Manager (and delegate) can log an NC; other users
    cannot.

2.  A logged NC receives a unique ID and notifies the receiving HoD.

3.  A cross-department NC records both raising and receiving
    departments.

4.  The receiving HoD can mark the NC Valid or Not valid; Not valid
    requires a reason and alerts the NC Manager.

5.  The NC Manager can uphold or overturn a dispute with rationale
    recorded.

6.  The receiving department can record root cause, corrective action,
    owner, target date and evidence, and only for its own NCs.

7.  An NC cannot be closed without evidence and NC Manager verification.

8.  All HoDs can view every NC across all departments, read-only.

9.  The dashboard shows correct counts for all statuses, and overdue
    items are flagged.

10. The register exports to Excel/PDF.

11. A pilot including a disputed cross-department NC is completed and
    reviewed by management.

# 11. Open Questions

1.  Who is the NC Manager, and who is the delegate?

2.  Does "HoD" mean Heads of all departments, and should HoDs see NC
    content for other departments in full, or only status and summary
    details?

3.  Should Management have the same read-only view as HoDs?

4.  How do departments report NCs to the NC Manager (email, chat, a
    simple request form)? Should we define a minimum information
    template?

5.  Who resolves a dispute the NC Manager cannot settle (Head of
    Quality, Management)?

6.  Do same-department NCs still need validation, or are they
    auto-validated?

7.  What is the validation deadline (3 working days proposed), and
    reminder and escalation intervals?

8.  Should severity (minor / major) be recorded?

9.  Should the raising department be able to add comments on a
    cross-department NC?

10. What is the record retention period, and should existing open NCs be
    migrated?

11. Which platform (Microsoft 365 or Google Workspace) will be used?
