import firebase_admin
from firebase_admin import credentials, firestore
from config import Config

_cred = credentials.Certificate(Config.FIREBASE_CRED_PATH)
firebase_admin.initialize_app(_cred)

db = firestore.client()

APPOINTMENTS_COLLECTION = "appointments"


def add_appointment(name: str, email: str, appointment_time: str, message: str = "", reminder_lead_minutes: int = 1):
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
 
