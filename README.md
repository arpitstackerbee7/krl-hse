# KRL HSE

Health, Safety and Environment module for KRL Infratech, built as a Frappe app on ERPNext v16
(Frappe 16.51, ERPNext 16.50). It follows the BRD "KRL_HSE_BRD_V1.0" and is delivered in phases.
Each phase has a demo, a KRL feedback gate and a sign-off test.

## What is in the app

| Phase | Content | Status |
|-------|---------|--------|
| 1 | Settings, document numbering, branches, roles, work order, workplace area, approval workflow | Built |
| 2 onward | See the "KRL HSE Phased Development Plan" | Not started |

Nothing is hard-coded to KRL. Everything KRL may want to change is a record that can be edited
in the desk: HSE Settings (prefix, number digits, financial-year start, number format, document
codes, the roles that see every branch), the masters (severity levels, worker categories, team
roles, contact roles), the roles, and the workflows.

### How setup works

`bench install-app krl_hse` and every `bench migrate` run `krl_hse.setup.install.ensure_setup()`.
It only adds what is missing and never overwrites an edit KRL has made:

* Custom fields on Branch: HSE Branch Code and "This is the Head Office".
* The 10 HSE roles from BRD section 14.1.
* Starting masters, document codes and workflows from `krl_hse/setup/data/*.json`. A master is loaded
  only while it is empty; a workflow only if it does not exist.
* Select permission on Branch for the HSE roles, so a user can choose a branch without reading it.

### Branches and who sees what

* A Frappe User Permission on Branch limits a user to that branch.
* Roles listed in HSE Settings under "Roles That See All Branches" (default Director, HSE Head,
  HO HSE Team), plus System Manager and Administrator, see every branch.
* A branch user who has no branch assigned sees nothing.
* A user limited to exactly one branch gets that branch filled in on every new HSE document
  (`krl_hse/public/js/hse_branch.js`).
* Every HSE document type with a `branch` field must be listed in `hse_branch_doctypes` in
  `hooks.py`. A test fails if one is missed.

### Managing sites

A site is an ERPNext Branch record. There is no limit on how many. Use **Manage Sites** on HSE Settings
(or the Branch list) to work with them.

* Director, HSE Head and HO HSE Team can create and edit a Branch, but not delete it. HR Manager, HR User
  and System Manager keep their usual rights. The head office roles get these rights once, at first setup,
  and after that KRL can change them in Role Permission Manager.
* Every site needs an HSE Branch Code (letters and digits, different for each site). Tick **Head Office**
  on the head office.
* **Disabled for HSE** retires a site: it is no longer offered when choosing a branch and no new HSE
  record can be made for it. Records already made stay as they are. Use this rather than deleting.
* The **People With Access** list on the Branch form shows who has been given the site, with buttons to
  give or remove it. Roles that see every branch are not listed.

### Document numbers

`{prefix}/{doc_code}/{branch}/{fy}/{job}/{seq}`, for example `KRL/WPAD/T/2026-27/0003`.
The format is set in HSE Settings. The running number is kept per branch, financial year and job.
"Preview a Number" on HSE Settings shows the next number without using it.

## Development

Use two sites, and never mix them.

| Site | Used for |
|------|----------|
| `krl.test` | Automated tests only. |
| `demo.test` | Demo data and checking the screens in a browser. |

```bash
# tests (78 so far)
bench --site krl.test run-tests --app krl_hse

# demo data (dev only, never runs on install; every record is named TEST ...)
bench --site demo.test execute krl_hse.demo.seed.load --kwargs "{'password': '<local password>'}"
bench --site demo.test execute krl_hse.demo.seed.clear              # archive
bench --site demo.test execute krl_hse.demo.seed.clear --kwargs "{'delete': 1}"   # delete
```

Demo users are `test.<key>@krl-demo.example`, one per role. The demo seed needs the branch names
below to exist, and it prints a line before it gives an existing Branch its HSE Branch Code:
`Head Office (HO)`, `KRL - KJBPSL (JSW) Jharsuguda (J)`, `KRL - VSP (RINL) (V)`, `Athagarh (T)`.
Branch codes J, V, T and HO are assumptions until KRL confirms them.

## Putting a phase on the KRL demo site

Nothing touches the KRL site until the project owner says "go". Before that:

1. Take a Frappe Cloud backup of the KRL site.
2. Switch outgoing email off, or limit it to the project owner.
3. Approve the TEST data and the dummy test users.

Then deploy the phase from the `develop` branch. On the first deploy, KRL needs to:

* Approve the HSE Branch Code on the three existing branches, and a new Head Office branch.
* Create Employee records for floor staff who will appear in area teams.

Employee and Customer select permissions are not granted by this app.

## Contributing

This app uses `pre-commit` for formatting and linting (ruff, eslint, prettier, pyupgrade):

```bash
cd apps/krl_hse
pre-commit install
```
