"""
Background job: runs every minute, finds appointments whose time is
coming up within their chosen reminder lead time (or has already
passed) and hasn't had a reminder sent yet, emails the person, then
marks it as sent so it's never emailed twice.
"""

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from firebase_service import get_pending_appointments, mark_reminder_sent
from email_service import send_appointment_reminder

# Fallback used only if an appointment somehow has no lead time saved
# (e.g. older records created before this feature existed).
DEFAULT_REMINDER_LEAD_MINUTES = 1


def check_and_send_reminders():
    now = datetime.now()
    pending = get_pending_appointments()

    for appt in pending:
        try:
            appt_time = datetime.fromisoformat(appt["appointment_time"])
        except (ValueError, KeyError):
            continue  # skip malformed records instead of crashing the job

        lead_minutes = appt.get("reminder_lead_minutes", DEFAULT_REMINDER_LEAD_MINUTES)
        try:
            lead_minutes = int(lead_minutes)
        except (TypeError, ValueError):
            lead_minutes = DEFAULT_REMINDER_LEAD_MINUTES

        send_at = appt_time - timedelta(minutes=lead_minutes)

        # Send once we've reached the "send_at" moment (appointment time
        # minus the lead time), so a once-a-minute check can't miss it.
        if now >= send_at:
            display_time = appt_time.strftime("%I:%M %p on %B %d, %Y")
            custom_message = appt.get("message", "")
            try:
                send_appointment_reminder(appt["name"], appt["email"], display_time, custom_message)
                mark_reminder_sent(appt["id"])
                print(f"[reminder] Sent to {appt['email']} for {display_time}")
            except Exception as e:
                # Don't mark as sent if the email failed -- it'll retry next minute.
                print(f"[reminder] FAILED for {appt['email']}: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_send_reminders, "interval", minutes=1, id="reminder_check")
    scheduler.start()
    return scheduler
