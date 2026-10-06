import os
import json
import hashlib
import shutil
import base64
from datetime import datetime
from flask import Flask, request, jsonify

LEDGER_FILE = "blockchain_ledger.json"
IPFS_DIR = "mock_ipfs_node"
PUB_KEYS_DIR = "public_keys"
USERS_FILE = "server_users.json"
ROOT_SECRET_KEY = "root_super_secret_password_change_me"

for d in [IPFS_DIR, PUB_KEYS_DIR]:
    if not os.path.exists(d): os.makedirs(d)
if not os.path.exists(LEDGER_FILE):
    with open(LEDGER_FILE, 'w', encoding='utf-8') as f: json.dump([], f)

if not os.path.exists(USERS_FILE):
    default_users = {
        "root": {"password": "87", "role": "Root"},
        "admin": {"password": "87", "role": "Administrator"}
    }
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_users, f, indent=4)

app = Flask(__name__)

def require_root_token(f):
    def decorator(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token != f"Bearer {ROOT_SECRET_KEY}":
            return jsonify({"error": "Unauthorized: Root key required"}), 403
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_db = json.load(f)
    except:
        users_db = {"root": {"password": "87", "role": "Root"}}

    if username in users_db and users_db[username]["password"] == password:
        return jsonify({"status": "success", "role": users_db[username]["role"]})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/register_key', methods=['POST'])
def api_register_key():
    data = request.json
    with open(os.path.join(PUB_KEYS_DIR, f"{data['username']}_public.pem"), "w", encoding='utf-8') as f:
        f.write(data['public_key_pem'])
    return jsonify({"status": "success"})

@app.route('/api/get_key/<username>', methods=['GET'])
def api_get_key(username):
    path = os.path.join(PUB_KEYS_DIR, f"{username}_public.pem")
    if os.path.exists(path):
        with open(path, "r", encoding='utf-8') as f: return jsonify({"public_key_pem": f.read()})
    return jsonify({"error": "Key not found"}), 404

@app.route('/api/upload_ipfs', methods=['POST'])
def api_upload_ipfs():
    payload_bytes = base64.b64decode(request.json['payload_base64'])
    content_hash = hashlib.sha256(payload_bytes).hexdigest()[:16]
    ipfs_cid = f"QmIPFS{content_hash}xyz"
    with open(os.path.join(IPFS_DIR, f"{ipfs_cid}.bin"), "wb") as f:
        f.write(payload_bytes)
    return jsonify({"ipfs_cid": ipfs_cid})

@app.route('/api/commit', methods=['POST'])
def api_commit():
    data = request.json
    with open(LEDGER_FILE, 'r', encoding='utf-8') as f: ledger = json.load(f)
    block_data = {
        "block_height": len(ledger) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signer_user": data['username'],
        "image_id": data['image_id'],
        "merkle_root_ciphertext": data['encrypted_merkle_root'], 
        "hash_bits": data['hash_bits'],
        "fingerprint": data['fingerprint'],
        "ipfs_cid": data['ipfs_cid'],
        "encrypted_logs": data['encrypted_logs'],                
        "digital_signature_hex": data['signature_hex'],          
        "status": "COMMITTED_AND_VERIFIED"
    }
    ledger.append(block_data)
    with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=4, ensure_ascii=False)
    return jsonify({"block_height": block_data['block_height']})

@app.route('/api/get_ledger', methods=['GET'])
@require_root_token
def api_get_ledger():
    with open(LEDGER_FILE, 'r', encoding='utf-8') as f: return jsonify(json.load(f))

@app.route('/api/get_stats', methods=['GET'])
@require_root_token
def api_get_stats():
    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8') as f: ledger = json.load(f)
    except:
        ledger = []
    return jsonify({
        "ledger_len": len(ledger),
        "ipfs_count": len(os.listdir(IPFS_DIR)),
        "keys_count": len(os.listdir(PUB_KEYS_DIR))
    })

@app.route('/api/clear_data', methods=['POST'])
@require_root_token
def api_clear_data():
    with open(LEDGER_FILE, 'w', encoding='utf-8') as f: json.dump([], f)
    shutil.rmtree(IPFS_DIR)
    os.makedirs(IPFS_DIR)
    shutil.rmtree(PUB_KEYS_DIR)
    os.makedirs(PUB_KEYS_DIR)
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)