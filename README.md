
# 🗂️ flask-fileserver

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A simple, internal-use file server with Azure AD authentication and per-user bucket-based access control.  

Ideal for internal homepages, admin panels, or internal tools that need secure file upload/download functionality without full cloud complexity.

---

## 🎯 Features

- Bucket + file system storage
- Per-user access control (`read`, `write`, `admin`)
- Microsoft Azure AD (Entra ID) token authentication
- Simple local file locking for safe concurrent writes
- Max file size limits via environment variable
- Extremely low operational overhead

---

## ⚙️ System Requirements

| Requirement | Description |
|-------------|-------------|
| Python | 3.8+ |
| Flask | Flask web server |
| Azure Tenant ID | Obtained via Entra |
| Azure Client ID | Obtained via Entra |
| FILE_STORAGE_LOCATION | Local folder path for storage |
| DEFAULT_ADMIN | Initial system admin username (UPN) |

Recommended: run behind nginx (or similar) in production.

---

## 🔧 Setup

1. Clone this repo
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create a `.env` file:
```
MSAL_TENANT_ID=<Azure Tenant ID>
MSAL_CLIENT_ID=<Azure Client ID>
FILE_STORAGE_LOCATION=/path/to/files
DEFAULT_ADMIN=<admin user UPN (email)>
MAX_FILE_SIZE_MB=100     # optional, defaults to 100
```
4. Run the server:
```bash
python app.py
```

This will create:
- `FILESERVER_BUCKETS.fsconfig`
- `FILESERVER_PERMISSIONS.fsconfig`

---

## 🚀 Production Deployment Notes

By default, `app.py` enables CORS only for `http://localhost:*`.  
If deploying behind nginx, or accessing from non-local clients, update:
```python
CORS(
    app,
    supports_credentials=True,
    origins=["http://your-frontend-url.com"],
    allow_headers=["Authorization", "Content-Type"]
)
```
Also modify `app.run()` to bind to `0.0.0.0` if you want to expose it:
```python
app.run(debug=True, host="0.0.0.0", port=5000)
```

---

## 🔑 Authentication

This server does **not issue tokens**.  
Clients must acquire an Azure AD token using MSAL (Microsoft Authentication Library) for their platform.  
Supply the token on every request:
```
Authorization: Bearer <your_token>
```

All tokens must be acquired on company-managed compliant devices (if Conditional Access applies).

---

## 📝 Permissions Model

| Level | Description |
|-------|-------------|
| admin | Full control of system or bucket |
| write | Can upload or delete files |
| read  | Can download or list files |
| remove | Used to remove user access |

`DEFAULT_ADMIN` automatically has `admin` on `SYSTEM` and all buckets.

---

## 📚 API Reference

All routes require:
```
Authorization: Bearer <Azure Token>
```

### Buckets

#### GET `/buckets`
Get list of user-accessible buckets.
```json
[
  {
    "bucket_id": "uuid",
    "bucket_name": "Reports",
    "created_by": "user@example.com",
    "created_at": "ISO8601"
  }
]
```

#### POST `/buckets`
Create a bucket.
```json
{ "bucket_name": "MyBucket" }
```
Returns:
```json
{ "bucket_id": "uuid" }
```

#### DELETE `/buckets/<bucket_id>`
Delete a bucket.
```json
{ "success": true }
```

---

### Files

#### GET `/buckets/<bucket_id>/files`
List files in a bucket.
```json
[
  {
    "file_id": "uuid",
    "file_name": "report.pdf",
    "file_size": 1.2,
    "created_by": "user@example.com",
    "created_at": "ISO8601"
  }
]
```

#### POST `/buckets/<bucket_id>/files`
Upload a file (`multipart/form-data`):
```
file = <binary file>
```
Returns:
```json
{ "file_id": "uuid" }
```

#### GET `/buckets/<bucket_id>/files/<file_id>`
Download a file.  
Returns file as attachment.

#### DELETE `/buckets/<bucket_id>/files/<file_id>`
Delete a file.
```json
{ "success": true }
```

---

### Permissions

#### POST `/buckets/<bucket_id>/permissions`
Set or remove a user’s permission:
```json
{
  "user": "user@example.com",
  "permission": "admin"   // or "read", "write", "remove"
}
```
Returns:
```json
{ "success": true }
```

---

### System Admins

#### POST `/system/admins`
Grant `SYSTEM` admin rights:
```json
{ "admin": "user@example.com" }
```

#### DELETE `/system/admins`
Revoke `SYSTEM` admin rights:
```json
{ "admin": "user@example.com" }
```

---

## 🧑‍💻 Example curl Requests

### Get Buckets
```bash
curl -H "Authorization: Bearer <your_token>" http://localhost:5000/buckets
```

### Create Bucket
```bash
curl -X POST -H "Authorization: Bearer <your_token>" -H "Content-Type: application/json" -d '{"bucket_name": "MyNewBucket"}' http://localhost:5000/buckets
```

### Upload File
```bash
curl -X POST -H "Authorization: Bearer <your_token>" -F "file=@/path/to/your/file.pdf" http://localhost:5000/buckets/<bucket_id>/files
```

---

## 🎯 Purpose & Scope

This system is designed to:
- Replace internal app file storage systems using base64 blobs
- Provide internal tools with simple secure file uploads
- Be easily auditable and fully controlled by developers

**This is NOT designed for:**
- Internet-scale workloads
- Unmanaged public access
- Extreme file sizes (>2GB)
- Multi-server high availability

Think: **internal team utility**, not **production cloud file service**.

---

## ⚠️ Disclaimer

This system is meant for **internal environments only**.  
Do not expose directly to the public internet.  
Deploy behind internal reverse proxies and firewalls for safety.

---

## ✅ Status

Production stable for small to medium internal use cases.  
Actively used in practice projects and prototype tooling.

---

# 🎉 Done!

This system is minimal by design and provides just enough features to be powerful without complexity.  
**Use it, customize it, improve it!**
