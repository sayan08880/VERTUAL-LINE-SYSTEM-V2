from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from config import Config
from firebase_service import (
    add_appointment,
    get_all_appointments,
    delete_appointment,
    delete_all_appointments,
)
from scheduler import start_scheduler

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/appointments", methods=["POST"])
def create_appointment():
    data = request.get_json()

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    appointment_time = (data.get("appointment_time") or "").strip()
    message = (data.get("message") or "").strip()  # optional, custom reminder text

    # How many minutes before the appointment to send the reminder.
    # Falls back to 1 minute if missing or invalid.
    try:
        reminder_lead_minutes = int(data.get("reminder_lead_minutes", 1))
        if reminder_lead_minutes < 0:
            reminder_lead_minutes = 1
    except (TypeError, ValueError):
        reminder_lead_minutes = 1

    if not name or not email or not appointment_time:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    try:
        appt_id = add_appointment(name, email, appointment_time, message, reminder_lead_minutes)
        return jsonify({"success": True, "id": appt_id, "message": "Appointment booked!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/appointments", methods=["GET"])
def list_appointments():
    try:
        appointments = get_all_appointments()
        return jsonify({"success": True, "appointments": appointments})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/appointments/<appt_id>", methods=["DELETE"])
def remove_appointment(appt_id):
    try:
        delete_appointment(appt_id)
        return jsonify({"success": True, "message": "Appointment deleted."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/appointments", methods=["DELETE"])
def remove_all_appointments():
    try:
        count = delete_all_appointments()
        return jsonify({"success": True, "message": f"Deleted {count} appointment(s)."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    # Starts the "check every minute, send reminder emails" background job.
    start_scheduler()
    app.run(debug=True, use_reloader=False)
    # use_reloader=False matters: Flask's debug reloader spawns a 2nd
    # process, which would start the scheduler twice and double-send emails.
