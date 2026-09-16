"""
Firebase Firestore connection + helper functions.

Setup (do this once):
1. Go to https://console.firebase.google.com -> your project
   -> Project Settings (gear icon) -> Service Accounts tab
   -> "Generate new private key" -> downloads a .json file
2. Rename it to serviceAccountKey.json and place it in this project's
   root folder (same folder as app.py).
3. Add serviceAccountKey.json to .gitignore (already done for you) so
   it never gets committed or uploaded anywhere.
4. In the Firebase Console, go to "Firestore Database" -> "Create database"
   if you haven't already (Firestore, NOT Realtime Database).
"""

import firebase_admin
from firebase_admin import credentials, firestore
from config import Config

_cred = credentials.Certificate(Config.FIREBASE_CRED_PATH)
firebase_admin.initialize_app(_cred)

db = firestore.client()

APPOINTMENTS_COLLECTION = "appointments"


def add_appointment(name: str, email: str, appointment_time: str, message: str = "", reminder_lead_minutes: int = 1):
    """
    appointment_time is expected as an ISO string, e.g. '2026-07-18T15:30'
    (this is exactly what an HTML <input type="datetime-local"> gives you).

    message is an optional custom reminder message the booker can type in;
    if left blank, the scheduler falls back to a default reminder text.

    reminder_lead_minutes is how many minutes before appointment_time the
    reminder email should go out (chosen by the booker in the dropdown).
    """
    doc_ref = db.collection(APPOINTMENTS_COLLECTION).document()
    doc_ref.set({
        "name": name,
        "email": email,
        "appointment_time": appointment_time,
        "message": message,
        "reminder_lead_minutes": reminder_lead_minutes,
        "reminder_sent": False,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return doc_ref.id


def get_all_appointments():
    docs = db.collection(APPOINTMENTS_COLLECTION).order_by("appointment_time").stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


def get_pending_appointments():
    """Appointments whose reminder email has not been sent yet."""
    docs = db.collection(APPOINTMENTS_COLLECTION).where("reminder_sent", "==", False).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


def mark_reminder_sent(doc_id: str):
    db.collection(APPOINTMENTS_COLLECTION).document(doc_id).update({"reminder_sent": True})


def delete_appointment(doc_id: str):
    """Deletes a single appointment by its Firestore document id."""
    db.collection(APPOINTMENTS_COLLECTION).document(doc_id).delete()


def delete_all_appointments():
    """Deletes every appointment in the collection. Used by 'Clear all'."""
    docs = db.collection(APPOINTMENTS_COLLECTION).stream()
    batch = db.batch()
    count = 0
    for doc in docs:
        batch.delete(doc.reference)
        count += 1
        # Firestore batches are capped at 500 writes, so flush periodically.
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    return count
 