from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta

from django.core.mail import send_mail
from django.db import transaction

from apps.audit import service as audit
from apps.audit.models import AuditEvent

from .models import Task


def _add_months(day: date, months: int) -> date:
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def next_due(task: Task) -> date | None:
    if task.due_date is None or task.recurrence == Task.Recurrence.NONE:
        return None
    n = task.recurrence_interval
    match task.recurrence:
        case Task.Recurrence.DAILY:
            return task.due_date + timedelta(days=n)
        case Task.Recurrence.WEEKLY:
            return task.due_date + timedelta(weeks=n)
        case Task.Recurrence.MONTHLY:
            return _add_months(task.due_date, n)
        case Task.Recurrence.YEARLY:
            return _add_months(task.due_date, 12 * n)
    return None


@transaction.atomic
def complete(task: Task) -> Task | None:
    """Mark a task done. A repeating task creates the next occurrence and returns it."""
    task.status = Task.Status.DONE
    task.completed_at = datetime.now(UTC)
    following = None
    due = next_due(task)
    if due is not None and task.next_task_id is None:
        following = Task.objects.create(
            domain=task.domain,
            title=task.title,
            description=task.description,
            assignee=task.assignee,
            priority=task.priority,
            due_date=due,
            recurrence=task.recurrence,
            recurrence_interval=task.recurrence_interval,
            reminder_days_before=task.reminder_days_before,
            linked_object_type=task.linked_object_type,
            linked_object_id=task.linked_object_id,
            custom_fields=task.custom_fields,
        )
        task.next_task = following
    task.save()
    return following


def should_remind(task: Task, today: date) -> bool:
    """Once when a task enters its reminder window, again on the day, then weekly if overdue."""
    if task.due_date is None or task.assignee_id is None:
        return False
    days_left = (task.due_date - today).days
    if days_left > task.reminder_days_before:
        return False
    last = task.last_reminded_on
    if last is None:
        return True
    if days_left == 0:
        return last < today
    if days_left < 0:
        return (today - last).days >= 7
    return False


def send_reminders(today: date | None = None, *, dry_run: bool = False) -> dict[str, int]:
    """Email each assignee one message listing the tasks that need a nudge today."""
    today = today or date.today()
    candidates = Task.objects.filter(
        status__in=Task.OPEN,
        due_date__isnull=False,
        assignee__isnull=False,
        assignee__is_active=True,
    ).select_related("assignee", "domain")
    by_user: dict = {}
    for task in candidates:
        if should_remind(task, today):
            by_user.setdefault(task.assignee, []).append(task)
    sent = 0
    for user, tasks in by_user.items():
        tasks.sort(key=lambda t: (t.due_date, t.priority))
        if not dry_run:
            lines = [
                f"- {t.title} ({t.domain.name}): "
                + ("overdue since " if t.due_date < today else "due ")
                + t.due_date.isoformat()
                for t in tasks
            ]
            send_mail(
                subject=f"{len(tasks)} task{'s' if len(tasks) != 1 else ''} need your attention",
                message="These tasks are due or overdue:\n\n" + "\n".join(lines) + "\n",
                from_email=None,
                recipient_list=[user.email],
            )
            Task.objects.filter(pk__in=[t.pk for t in tasks]).update(last_reminded_on=today)
            audit.record(
                AuditEvent.Action.OTHER,
                object_type="tasks.task",
                object_repr=f"reminder to {user.email}",
                changes={"tasks": [str(t.pk) for t in tasks]},
            )
        sent += 1
    return {"recipients": sent, "tasks": sum(len(t) for t in by_user.values())}
