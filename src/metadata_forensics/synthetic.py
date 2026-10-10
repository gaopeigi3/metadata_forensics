from random import Random
import pandas as pd

def generate(n_patients=4000, seed=42):
    """Preserve original random draw order; no files or global RNG mutations."""
    if n_patients < 1:
        raise ValueError("n_patients must be positive")


    random = Random(seed)

    patients = []

    for i in range(1, n_patients + 1):
        patient_uid = f"PT{i:04d}"

        sex = random.choice(["M", "F"])

        birth_date = (
            f"{random.randint(1950, 1990)}-"
            f"{random.randint(1, 12):02d}-"
            f"{random.randint(1, 28):02d}"
        )

        diagnosis = random.choice([
            "AML",
            # "ALL",
            # "CML",
            # "CLL"
        ])

        diagnosis_date = (
            f"{random.randint(2010, 2020)}-"
            f"{random.randint(1, 12):02d}-"
            f"{random.randint(1, 28):02d}"
        )

        patients.append(
            (
                patient_uid,
                sex,
                birth_date,
                diagnosis,
                diagnosis_date
            )
        )

    patient_identifiers = []

    for i in range(1, n_patients + 1):
        patient_uid = f"PT{i:04d}"

        clinical_id = f"UPIN{i + 100:03d}"
        lab_id = f"P{i + 10:03d}"

        patient_identifiers.append(
            (
                patient_uid,
                "clinical",
                clinical_id
            )
        )

        patient_identifiers.append(
            (
                patient_uid,
                "lab",
                lab_id
            )
        )

    from datetime import datetime, timedelta

    clinical_visits = []
    visit_counter = 1

    for patient in patients:
        patient_uid, sex, birth_date, diagnosis, diagnosis_date = patient

        diagnosis_dt = datetime.strptime(diagnosis_date, "%Y-%m-%d")

        # diagnosis visit
        clinical_visits.append(
            (
                f"V{visit_counter:04d}",
                patient_uid,
                diagnosis_dt.strftime("%Y-%m-%d"),
                "Diagnosis"
            )
        )
        visit_counter += 1

        # follow-up visits
        n_followups = random.randint(2, 6)
        current_date = diagnosis_dt

        for _ in range(n_followups):
            current_date += timedelta(
                days=random.randint(20, 120)
            )

            clinical_visits.append(
                (
                    f"V{visit_counter:04d}",
                    patient_uid,
                    current_date.strftime("%Y-%m-%d"),
                    "Follow-up"
                )
            )

            visit_counter += 1

    samples = []
    sample_counter = 1

    for visit_uid, patient_uid, visit_date, visit_type in clinical_visits:

        visit_dt = datetime.strptime(visit_date, "%Y-%m-%d")

        # Diagnosis visits are more likely to trigger sampling
        if visit_type == "Diagnosis":
            sampling_probability = 0.85
        else:
            sampling_probability = 0.45

        if random.random() > sampling_probability:
            continue

        sample_types = random.choice([
            ["PB"],
            ["BM"],
            ["PB", "BM"]
        ])

        collection_dt = visit_dt + timedelta(
            days=random.randint(-1, 2)
        )

        for sample_type in sample_types:
            sample_id = f"S{sample_counter:04d}"

            samples.append(
                (
                    sample_id,
                    patient_uid,
                    visit_uid,
                    sample_type,
                    collection_dt.strftime("%Y-%m-%d")
                )
            )

            sample_counter += 1

    # Build lookup tables

    patient_lookup = {
        patient_uid: {
            "sex": sex,
            "birth_date": birth_date,
            "diagnosis": diagnosis,
            "diagnosis_date": diagnosis_date,
        }
        for patient_uid, sex, birth_date, diagnosis, diagnosis_date in patients
    }

    clinical_id_lookup = {
        patient_uid: identifier_value
        for patient_uid, identifier_system, identifier_value in patient_identifiers
        if identifier_system == "clinical"
    }

    # doctor side

    clinical_rows = []

    for visit_uid, patient_uid, visit_date, visit_type in clinical_visits:

        patient = patient_lookup[patient_uid]
        clinical_id = clinical_id_lookup[patient_uid]

        birth_year = patient["birth_date"][:4]

        clinical_rows.append(
            (
                visit_uid,
                clinical_id,
                visit_date,
                visit_type,
                patient["sex"],
                birth_year,
                patient["diagnosis"],
            )
        )

    # lab side
    lab_id_lookup = {
        patient_uid: identifier_value
        for patient_uid, identifier_system, identifier_value in patient_identifiers
        if identifier_system == "lab"
    }

    sample_rows = []

    for sample_id, patient_uid, visit_uid, sample_type, collection_date in samples:

        lab_id = lab_id_lookup[patient_uid]

        sample_rows.append(
            (
                sample_id,
                lab_id,
                sample_type,
                collection_date,
            )
        )
    clinical = pd.DataFrame(clinical_rows, columns=['Visit_ID','Patient_ID','Visit_Date','Visit_Type','Sex','Birth_Year','Diagnosis'])
    lab = pd.DataFrame(sample_rows, columns=['Sample_ID','Patient_No','Sample_Type','Collection_Date'])
    identifiers = pd.DataFrame(patient_identifiers, columns=['patient_uid','system','identifier'])
    clinical['Visit_Date'] = pd.to_datetime(clinical['Visit_Date'])
    lab['Collection_Date'] = pd.to_datetime(lab['Collection_Date'])
    return clinical, lab, identifiers
