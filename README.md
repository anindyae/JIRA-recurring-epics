# JIRA Recurring Epic Creator

A simple utility to automatically create recurring JIRA epics with minimal input. Perfect for teams that need to create the same set of epics every month.

## Features

- 📋 **Template-based** - Define epics once, create them repeatedly
- 🔄 **Auto date substitution** - Month, year, quarter auto-filled
- 📅 **Working day dates** - Start/end dates set to first/last working days
- 🔒 **Auto-close previous** - Previous month's epics closed automatically
- ⚠️ **Duplicate protection** - Warns if epics already exist for the month
- 🔍 **Dry-run mode** - Preview before creating

## Quick Start

### 1. Setup

```batch
REM Install dependencies (one time)
pip install -r requirements.txt

REM Copy and configure credentials
copy .env.example .env
REM Edit .env with your JIRA details
```

### 2. Configure `.env`

```ini
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=PROJ
```

> **Get API Token:** https://id.atlassian.com/manage-profile/security/api-tokens

### 3. Test Connection

```batch
create_epics.bat test-connection
```

### 4. Create Epics

```batch
REM Create all CC Gantt epics for current month
create_epics.bat create -t cc-gantt-meetings -t cc-gantt-test-setup -t cc-gantt-qa-tasks -t cc-gantt-automation-tasks

REM Or preview first (dry run)
create_epics.bat --dry-run create -t cc-gantt-meetings -t cc-gantt-test-setup -t cc-gantt-qa-tasks -t cc-gantt-automation-tasks
```

## Commands

| Command | Description |
|---------|-------------|
| `create_epics.bat create` | Create epics (prompts if duplicates exist) |
| `create_epics.bat create -y` | Create without confirmation |
| `create_epics.bat --dry-run create` | Preview what will be created |
| `create_epics.bat create --month 3 --year 2026` | Create for specific month |
| `create_epics.bat create --no-close-previous` | Don't close previous month's epics |
| `create_epics.bat list-templates` | Show available templates |
| `create_epics.bat preview <template>` | Preview a specific template |
| `create_epics.bat test-connection` | Test JIRA connection |

### Options

| Option | Description |
|--------|-------------|
| `-t, --templates` | Specify which templates to create (can use multiple) |
| `--month` | Month number (1-12), defaults to current |
| `--year` | Year, defaults to current |
| `--force` | Create even if epic with same name exists |
| `--no-close-previous` | Don't auto-close previous month's epics |
| `-y, --yes` | Skip confirmation prompts |
| `--dry-run` | Preview without creating |

## CC Gantt Epics

The following epics are created each month:

| Epic | Description |
|------|-------------|
| **Meetings - CC Gantt - Mon'YY** | Time spent in calls and discussions |
| **Test Setup and Documentation - CC Gantt - Mon'YY** | Build generation, test case documentation |
| **QA Tasks - CC Gantt - Mon'YY** | Manual QA tasks, feature testing, bug verification |
| **Automation Tasks - CC Gantt - Mon'YY** | Test automation work |

Each epic gets:
- **Start Date**: First working day of the month (Mon-Fri)
- **End Date**: Last working day of the month (Mon-Fri)
- **Labels**: `QA_Tasks`, `recurring`

## Customizing Templates

Edit `templates/cc_gantt_templates.yaml` to modify epics:

```yaml
templates:
  - name: cc-gantt-meetings
    summary: "Meetings - CC Gantt - {month_short}'{year_short}"
    description: |
      Your description here for {month_name} {year}.
    labels:
      - QA_Tasks
      - recurring
    priority: Medium
```

### Available Variables

| Variable | Example |
|----------|---------|
| `{month}` | `02` |
| `{month_name}` | `February` |
| `{month_short}` | `Feb` |
| `{year}` | `2026` |
| `{year_short}` | `26` |
| `{quarter}` | `Q1` |

## Project Structure

```
JIRA-recurring-epics/
├── create_epics.bat           # Run this to create epics
├── jira_epic_creator.py       # Main script
├── .env                       # Your credentials (git-ignored)
├── .env.example               # Credential template
├── requirements.txt           # Python dependencies
└── templates/
    └── cc_gantt_templates.yaml  # Epic definitions
```

## Monthly Workflow

Each month, just run:

```batch
create_epics.bat create -t cc-gantt-meetings -t cc-gantt-test-setup -t cc-gantt-qa-tasks -t cc-gantt-automation-tasks
```

This will:
1. ✅ Close previous month's CC Gantt epics
2. ✅ Create 4 new epics for current month
3. ✅ Set start/end dates to working days

## Troubleshooting

### "Missing required environment variables"
Create a `.env` file with your JIRA credentials. Copy from `.env.example`.

### "401 Unauthorized"
- Verify your JIRA email and API token
- Ensure API token hasn't expired
- Check account has permission to create issues

### "Connection failed"
- Check JIRA_SERVER URL is correct (include https://)
- Verify network connectivity

### Epics not closing
Different JIRA workflows have different transition names. The tool tries: Done, Close, Closed, Complete, Completed, Resolve, Resolved.

## License

MIT License
