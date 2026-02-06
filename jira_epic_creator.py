#!/usr/bin/env python
"""
JIRA Recurring Epic Creator - Single file utility
Creates recurring JIRA epics with minimal input.
"""
import os
import sys
import yaml
import click
import calendar
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from jira import JIRA
from jira.exceptions import JIRAError
from rich.console import Console
from rich.table import Table

console = Console()


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Configuration class for JIRA connection and project settings."""
    
    def __init__(self, env_path: str = None):
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
        
        self.jira_server = os.getenv("JIRA_SERVER")
        self.jira_email = os.getenv("JIRA_EMAIL")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN")
        self.project_key = os.getenv("JIRA_PROJECT_KEY")
        
        self._validate()
    
    def _validate(self):
        missing = []
        if not self.jira_server:
            missing.append("JIRA_SERVER")
        if not self.jira_email:
            missing.append("JIRA_EMAIL")
        if not self.jira_api_token:
            missing.append("JIRA_API_TOKEN")
        if not self.project_key:
            missing.append("JIRA_PROJECT_KEY")
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please create a .env file based on .env.example"
            )


# =============================================================================
# Date Utilities
# =============================================================================

def get_first_working_day(year: int, month: int) -> date:
    """Get the first working day (Mon-Fri) of a month."""
    first_day = date(year, month, 1)
    while first_day.weekday() >= 5:
        first_day += timedelta(days=1)
    return first_day


def get_last_working_day(year: int, month: int) -> date:
    """Get the last working day (Mon-Fri) of a month."""
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    while last_day.weekday() >= 5:
        last_day -= timedelta(days=1)
    return last_day


# =============================================================================
# Templates
# =============================================================================

class EpicTemplate:
    """Represents a single epic template."""
    
    def __init__(self, name: str, summary_template: str, description_template: str = "",
                 labels: List[str] = None, components: List[str] = None,
                 priority: str = "Medium", custom_fields: Dict[str, Any] = None,
                 stories: List[Dict[str, Any]] = None):
        self.name = name
        self.summary_template = summary_template
        self.description_template = description_template
        self.labels = labels or []
        self.components = components or []
        self.priority = priority
        self.custom_fields = custom_fields or {}
        self.stories = stories or []
    
    def render(self, **context) -> Dict[str, Any]:
        now = datetime.now()
        default_context = {
            "month": now.strftime("%m"),
            "month_name": now.strftime("%B"),
            "month_short": now.strftime("%b"),
            "year": now.strftime("%Y"),
            "year_short": now.strftime("%y"),
            "quarter": f"Q{(now.month - 1) // 3 + 1}",
        }
        default_context.update(context)
        context = default_context
        
        rendered = {
            "summary": self.summary_template.format(**context),
            "description": self.description_template.format(**context),
            "labels": self.labels,
            "components": self.components,
            "priority": self.priority,
            "custom_fields": self.custom_fields,
        }
        
        if self.stories:
            rendered["stories"] = []
            for story in self.stories:
                rendered_story = {
                    "summary": story.get("summary", "").format(**context),
                    "description": story.get("description", "").format(**context),
                    "story_points": story.get("story_points"),
                    "labels": story.get("labels", []),
                }
                rendered["stories"].append(rendered_story)
        
        return rendered


class TemplateManager:
    """Manages loading and organizing epic templates."""
    
    def __init__(self, templates_dir: str = None):
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent / "templates"
        
        self.templates: Dict[str, EpicTemplate] = {}
        self._load_templates()
    
    def _load_templates(self):
        if not self.templates_dir.exists():
            return
        
        for template_file in self.templates_dir.glob("*.yaml"):
            self._load_template_file(template_file)
        for template_file in self.templates_dir.glob("*.yml"):
            self._load_template_file(template_file)
    
    def _load_template_file(self, file_path: Path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data:
            return
        
        templates = data.get("templates", [data])
        
        for template_data in templates:
            template = EpicTemplate(
                name=template_data.get("name"),
                summary_template=template_data.get("summary"),
                description_template=template_data.get("description", ""),
                labels=template_data.get("labels", []),
                components=template_data.get("components", []),
                priority=template_data.get("priority", "Medium"),
                custom_fields=template_data.get("custom_fields", {}),
                stories=template_data.get("stories", [])
            )
            self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[EpicTemplate]:
        return self.templates.get(name)
    
    def get_all_templates(self) -> List[EpicTemplate]:
        return list(self.templates.values())
    
    def list_template_names(self) -> List[str]:
        return list(self.templates.keys())


# =============================================================================
# JIRA Client
# =============================================================================

class JiraClient:
    """Wrapper around the JIRA API client."""
    
    def __init__(self, config: Config):
        self.config = config
        self._client = JIRA(
            server=self.config.jira_server,
            basic_auth=(self.config.jira_email, self.config.jira_api_token)
        )
    
    def create_epic(self, project_key: str, summary: str, description: str = "",
                    labels: List[str] = None, components: List[str] = None,
                    priority: str = "Medium", custom_fields: Dict[str, Any] = None,
                    start_date: date = None, end_date: date = None) -> Any:
        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Epic"},
            "priority": {"name": priority},
        }
        
        if labels:
            fields["labels"] = labels
        if components:
            fields["components"] = [{"name": c} for c in components]
        if custom_fields:
            fields.update(custom_fields)
        
        if start_date:
            start_field = self._get_field_id(["Start date", "Start Date", "startDate"])
            if start_field:
                fields[start_field] = start_date.strftime("%Y-%m-%d")
        
        if end_date:
            fields["duedate"] = end_date.strftime("%Y-%m-%d")
        
        try:
            return self._client.create_issue(fields=fields)
        except JIRAError as e:
            raise RuntimeError(f"Failed to create epic: {e.text}") from e
    
    def _get_field_id(self, field_names: List[str]) -> Optional[str]:
        fields = self._client.fields()
        for field in fields:
            if field["name"] in field_names:
                return field["id"]
        return None
    
    def epic_exists(self, project_key: str, summary: str) -> bool:
        jql = f'project = "{project_key}" AND issuetype = Epic AND summary ~ "\\"{summary}\\""'
        results = self._client.search_issues(jql, maxResults=1)
        return len(results) > 0
    
    def get_project(self, project_key: str) -> Any:
        return self._client.project(project_key)
    
    def test_connection(self) -> bool:
        try:
            self._client.myself()
            return True
        except JIRAError:
            return False
    
    def close_epic(self, issue_key: str) -> bool:
        try:
            transitions = self._client.transitions(issue_key)
            close_transition = None
            for t in transitions:
                if t["name"].lower() in ["done", "close", "closed", "complete", "completed", "resolve", "resolved"]:
                    close_transition = t["id"]
                    break
            
            if close_transition:
                self._client.transition_issue(issue_key, close_transition)
                return True
            return False
        except JIRAError:
            return False
    
    def find_previous_month_epics(self, project_key: str, summary_pattern: str,
                                   current_month: int, current_year: int) -> List[Any]:
        jql = (
            f'project = "{project_key}" '
            f'AND issuetype = Epic '
            f'AND summary ~ "{summary_pattern}" '
            f'AND status != Done '
            f'AND status != Closed'
        )
        
        try:
            issues = self._client.search_issues(jql, maxResults=100)
            current_suffix = self._get_month_suffix(current_month, current_year)
            return [issue for issue in issues if current_suffix not in issue.fields.summary]
        except JIRAError:
            return []
    
    def find_current_month_epics(self, project_key: str, summary_pattern: str,
                                  month: int, year: int) -> List[Any]:
        month_suffix = self._get_month_suffix(month, year)
        jql = (
            f'project = "{project_key}" '
            f'AND issuetype = Epic '
            f'AND summary ~ "{summary_pattern}" '
            f'AND summary ~ "{month_suffix}"'
        )
        
        try:
            return list(self._client.search_issues(jql, maxResults=100))
        except JIRAError:
            return []
    
    def _get_month_suffix(self, month: int, year: int) -> str:
        month_short = date(year, month, 1).strftime("%b")
        year_short = str(year)[-2:]
        return f"{month_short}'{year_short}"


# =============================================================================
# Epic Creator
# =============================================================================

class EpicCreator:
    """Main class for creating recurring epics from templates."""
    
    def __init__(self, config: Config = None, templates_dir: str = None, dry_run: bool = False):
        self.config = config or Config()
        self.template_manager = TemplateManager(templates_dir)
        self.dry_run = dry_run
        self._jira_client = None
    
    @property
    def jira_client(self) -> JiraClient:
        if self._jira_client is None:
            self._jira_client = JiraClient(self.config)
        return self._jira_client
    
    def check_existing_month_epics(self, month: int, year: int) -> List[Any]:
        return self.jira_client.find_current_month_epics(
            project_key=self.config.project_key,
            summary_pattern="CC Gantt",
            month=month,
            year=year
        )
    
    def create_epic_from_template(self, template_name: str, skip_if_exists: bool = True,
                                   start_date=None, end_date=None, **context) -> Optional[Dict[str, Any]]:
        template = self.template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        rendered = template.render(**context)
        
        if skip_if_exists and not self.dry_run:
            if self.jira_client.epic_exists(self.config.project_key, rendered["summary"]):
                console.print(f"[yellow]⚠ Skipping:[/yellow] Epic already exists: {rendered['summary']}")
                return None
        
        result = {"template": template_name, "epic": None}
        
        if self.dry_run:
            console.print(f"[blue][DRY RUN][/blue] Would create epic: {rendered['summary']}")
            if start_date and end_date:
                console.print(f"[blue][DRY RUN][/blue]   Start: {start_date}, End: {end_date}")
            result["epic"] = {"key": "DRY-RUN", "summary": rendered["summary"]}
        else:
            epic = self.jira_client.create_epic(
                project_key=self.config.project_key,
                summary=rendered["summary"],
                description=rendered["description"],
                labels=rendered["labels"],
                components=rendered["components"],
                priority=rendered["priority"],
                custom_fields=rendered.get("custom_fields", {}),
                start_date=start_date,
                end_date=end_date
            )
            date_info = f" ({start_date} to {end_date})" if start_date and end_date else ""
            console.print(f"[green]✓ Created epic:[/green] {epic.key} - {rendered['summary']}{date_info}")
            result["epic"] = {"key": epic.key, "summary": rendered["summary"]}
        
        return result
    
    def create_monthly_epics(self, template_names: List[str] = None, month: int = None,
                              year: int = None, skip_if_exists: bool = True,
                              close_previous: bool = True, confirmed: bool = False) -> Any:
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        
        start_date = get_first_working_day(year, month)
        end_date = get_last_working_day(year, month)
        
        date_obj = datetime(year, month, 1)
        context = {
            "month": date_obj.strftime("%m"),
            "month_name": date_obj.strftime("%B"),
            "month_short": date_obj.strftime("%b"),
            "year": date_obj.strftime("%Y"),
            "year_short": date_obj.strftime("%y"),
            "quarter": f"Q{(month - 1) // 3 + 1}",
        }
        
        templates = template_names if template_names else self.template_manager.list_template_names()
        
        # Check for existing epics
        if not self.dry_run and not confirmed:
            existing_epics = self.check_existing_month_epics(month, year)
            if existing_epics:
                return {"requires_confirmation": True, "existing_epics": existing_epics, "context": context}
        
        console.print(f"\n[bold]Creating epics for {context['month_name']} {context['year']}[/bold]")
        console.print(f"[dim]Start date: {start_date} (first working day)[/dim]")
        console.print(f"[dim]End date: {end_date} (last working day)[/dim]\n")
        
        # Close previous month's epics
        if close_previous and not self.dry_run:
            self._close_previous_month_epics(month, year)
        elif close_previous and self.dry_run:
            console.print("[blue][DRY RUN][/blue] Would close previous month's epics\n")
        
        results = []
        for template_name in templates:
            try:
                result = self.create_epic_from_template(
                    template_name, skip_if_exists=skip_if_exists,
                    start_date=start_date, end_date=end_date, **context
                )
                if result:
                    results.append(result)
            except Exception as e:
                console.print(f"[red]✗ Error creating {template_name}:[/red] {str(e)}")
        
        return results
    
    def _close_previous_month_epics(self, current_month: int, current_year: int):
        console.print("[yellow]Closing previous month's epics...[/yellow]")
        
        previous_epics = self.jira_client.find_previous_month_epics(
            project_key=self.config.project_key,
            summary_pattern="CC Gantt",
            current_month=current_month,
            current_year=current_year
        )
        
        if not previous_epics:
            console.print("[dim]No previous month epics found to close.[/dim]\n")
            return
        
        for epic in previous_epics:
            success = self.jira_client.close_epic(epic.key)
            if success:
                console.print(f"[green]✓ Closed:[/green] {epic.key} - {epic.fields.summary}")
            else:
                console.print(f"[yellow]⚠ Could not close:[/yellow] {epic.key} (may need manual transition)")
        console.print()
    
    def list_templates(self):
        templates = self.template_manager.get_all_templates()
        if not templates:
            console.print("[yellow]No templates found.[/yellow]")
            return
        
        table = Table(title="Available Epic Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Summary Template", style="white")
        table.add_column("Labels", style="green")
        
        for template in templates:
            summary = template.summary_template[:50] + "..." if len(template.summary_template) > 50 else template.summary_template
            table.add_row(template.name, summary, ", ".join(template.labels[:3]))
        
        console.print(table)
    
    def preview_template(self, template_name: str, **context):
        template = self.template_manager.get_template(template_name)
        if not template:
            console.print(f"[red]Template '{template_name}' not found[/red]")
            return
        
        rendered = template.render(**context)
        
        console.print(f"\n[bold]Preview of '{template_name}'[/bold]\n")
        console.print(f"[cyan]Summary:[/cyan] {rendered['summary']}")
        console.print(f"[cyan]Priority:[/cyan] {rendered['priority']}")
        console.print(f"[cyan]Labels:[/cyan] {', '.join(rendered['labels'])}")
        console.print(f"\n[cyan]Description:[/cyan]\n{rendered['description']}")


# =============================================================================
# CLI Commands
# =============================================================================

@click.group()
@click.option("--dry-run", is_flag=True, help="Preview changes without creating issues")
@click.pass_context
def cli(ctx, dry_run):
    """JIRA Recurring Epics - Create recurring epics with minimal input."""
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run


@cli.command()
@click.pass_context
def list_templates(ctx):
    """List all available epic templates."""
    try:
        creator = EpicCreator(dry_run=ctx.obj["dry_run"])
        creator.list_templates()
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@cli.command()
@click.argument("template_name")
@click.option("--month", type=int, help="Month number (1-12)")
@click.option("--year", type=int, help="Year (e.g., 2026)")
@click.pass_context
def preview(ctx, template_name, month, year):
    """Preview what an epic will look like."""
    try:
        creator = EpicCreator(dry_run=True)
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        
        date_obj = datetime(year, month, 1)
        context = {
            "month": date_obj.strftime("%m"),
            "month_name": date_obj.strftime("%B"),
            "month_short": date_obj.strftime("%b"),
            "year": date_obj.strftime("%Y"),
            "year_short": date_obj.strftime("%y"),
            "quarter": f"Q{(month - 1) // 3 + 1}",
        }
        creator.preview_template(template_name, **context)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@cli.command()
@click.option("--templates", "-t", multiple=True, help="Template names to create")
@click.option("--month", type=int, help="Month number (1-12). Defaults to current.")
@click.option("--year", type=int, help="Year. Defaults to current year.")
@click.option("--force", is_flag=True, help="Create even if epic already exists")
@click.option("--no-close-previous", is_flag=True, help="Don't close previous month's epics")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.pass_context
def create(ctx, templates, month, year, force, no_close_previous, yes):
    """Create monthly recurring epics."""
    try:
        creator = EpicCreator(dry_run=ctx.obj["dry_run"])
        template_names = list(templates) if templates else None
        
        results = creator.create_monthly_epics(
            template_names=template_names,
            month=month,
            year=year,
            skip_if_exists=not force,
            close_previous=not no_close_previous,
            confirmed=yes
        )
        
        # Handle confirmation
        if isinstance(results, dict) and results.get("requires_confirmation"):
            existing = results["existing_epics"]
            ctx_data = results["context"]
            
            console.print(f"\n[yellow]⚠ Warning:[/yellow] Found {len(existing)} existing epic(s) for {ctx_data['month_name']} {ctx_data['year']}:\n")
            for epic in existing:
                console.print(f"  • {epic.key} - {epic.fields.summary}")
            
            console.print()
            if not click.confirm("Create new epics anyway? (This may create duplicates)"):
                console.print("[yellow]Aborted.[/yellow]")
                return
            
            results = creator.create_monthly_epics(
                template_names=template_names, month=month, year=year,
                skip_if_exists=not force, close_previous=not no_close_previous, confirmed=True
            )
        
        if isinstance(results, list):
            console.print(f"\n[bold green]Created {len(results)} epic(s)[/bold green]")
    
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {str(e)}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@cli.command()
def test_connection():
    """Test the JIRA connection."""
    try:
        config = Config()
        console.print(f"Connecting to {config.jira_server}...")
        client = JiraClient(config)
        
        if client.test_connection():
            console.print("[bold green]✓ Connection successful![/bold green]")
            project = client.get_project(config.project_key)
            console.print(f"Project: {project.name} ({project.key})")
        else:
            console.print("[bold red]✗ Connection failed[/bold red]")
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {str(e)}")
    except Exception as e:
        console.print(f"[red]Connection error:[/red] {str(e)}")


if __name__ == "__main__":
    cli()
