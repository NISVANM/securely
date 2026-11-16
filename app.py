from flask import Flask, jsonify

app = Flask(__name__)

PATIENTS = [
    {"id": 1, "name": "Test Patient A", "condition": "Hypertension"},
    {"id": 2, "name": "Test Patient B", "condition": "Diabetes"},
]


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/patients")
def patients():
    return jsonify(PATIENTS)
