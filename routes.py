from flask import Blueprint, request, jsonify, send_file
from token_verification import verifyUser
import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
import time
import shutil

api_blueprint = Blueprint('api', __name__)

# Enable loading environment variables from .env file as well as system environment variables
load_dotenv()

file_storage_location = os.getenv("FILE_STORAGE_LOCATION")

if not file_storage_location:
    raise ValueError("FILE_STORAGE_LOCATION is not set")

# Create the config file if it doesn't exist
if not os.path.exists(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig")):
    with open(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig"), "w") as f:
        json.dump({}, f)

# Create the permissions file if it doesn't exist
if not os.path.exists(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig")):
    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "w") as f:
        DEFAULT_ADMIN = os.getenv("DEFAULT_ADMIN")
        if not DEFAULT_ADMIN:
            raise ValueError("DEFAULT_ADMIN is not set")
        json.dump({DEFAULT_ADMIN: {"permissions": {"SYSTEM": "admin", "*": "admin"}, "buckets": ["*"]}}, f)

MAXIMUM_FILE_SIZE = os.getenv("MAXIMUM_FILE_SIZE")

if not MAXIMUM_FILE_SIZE:
    raise ValueError("MAXIMUM_FILE_SIZE is not set")

MAXIMUM_FILE_SIZE = int(MAXIMUM_FILE_SIZE)


# This is a helper function to get the permissions for the user based on the bucket (read, write, admin)
def get_permissions(user, bucket):

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "r") as f:
        permissions = json.load(f)

    if user not in permissions:
        return None
    
    if "*" in permissions[user]["permissions"] and bucket != "SYSTEM":
        return permissions[user]["permissions"]["*"]

    if bucket not in permissions[user]["permissions"]:
        return None

    return permissions[user]["permissions"][bucket]


# This function authenticates the user and checks if they have access to the channel (if channel_id is provided)
@api_blueprint.before_request
def verify_token():
    try:
        if request.method == "OPTIONS":
            return jsonify({"success": True})

        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "No token provided"}), 401
        else:

            if token.startswith("Bearer "):
                token = token.split(" ")[1]

            user = verifyUser(token, file_storage_location)
            if not user:
                return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Get all the buckets for the user
@api_blueprint.route("/buckets", methods=["GET"])
def get_buckets():
    
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "r") as f:
        permissions = json.load(f)

    if user not in permissions:
        return jsonify([])

    # This is a list of all the channels the user has access to
    buckets = permissions[user]["buckets"]

    # Each bucket is a subfolder in the file_storage_location so we need to get all the subfolders
    if "*" in buckets:
        buckets = [f for f in os.listdir(file_storage_location) if os.path.isdir(os.path.join(file_storage_location, f))]

    # Get the bucket information from the FILESERVER_BUCKETS.fsconfig file
    with open(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig"), "r") as f:
        buckets_info = json.load(f)

    # Add the bucket information to the buckets list
    bucket_data = []
    for bucket in buckets:
        bucket_data.append({
            "bucket_id": bucket,
            "bucket_name": buckets_info[bucket]["name"],
            "created_by": buckets_info[bucket]["created_by"],
            "created_at": buckets_info[bucket]["created_at"]
        })

    return jsonify(bucket_data)


# Create a new bucket
@api_blueprint.route("/buckets", methods=["POST"])
def create_bucket():
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    permissions = get_permissions(user, "SYSTEM")

    if permissions not in ["admin", "write"]:
        return jsonify({"error": "You do not have permission to create a new bucket"}), 403

    data = request.get_json()

    bucket_name = data["bucket_name"] if "bucket_name" in data else None

    if not bucket_name:
        return jsonify({"error": "Bucket name is required"}), 400

    bucket_id = str(uuid.uuid4())

    while os.path.exists(os.path.join(file_storage_location, bucket_id)):
        bucket_id = str(uuid.uuid4())

    bucket_path = os.path.join(file_storage_location, bucket_id)

    os.makedirs(bucket_path)

    # Add the bucket name and id to the FILESERVER_BUCKETS.fsconfig file... it is a json file that contains all the buckets

    # Wait for the buckets write lock to be released
    while os.path.exists(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig.lock")):
        time.sleep(0.1)

    # Create the buckets write lock
    with open(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig"), "r") as f:
        buckets = json.load(f)

    buckets[bucket_id] = {
        "name": bucket_name,
        "created_by": user,
        "created_at": datetime.now().isoformat()
    }

    with open(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig"), "w") as f:
        json.dump(buckets, f)

    # Release the buckets write lock
    os.remove(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig.lock"))

    # Add the bucket to the user's permissions

    # Wait for the permissions write lock to be released
    while os.path.exists(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock")):
        time.sleep(0.1)

    # Create the permissions write lock
    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "r") as f:
        permissions = json.load(f)

    permissions[user]["buckets"].append(bucket_id)
    permissions[user]["permissions"][bucket_id] = "admin"

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "w") as f:
        json.dump(permissions, f)

    # Release the permissions write lock
    os.remove(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"))

    # Add the bucket's config to the bucket
    with open(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig"), "w") as f:
        json.dump({"files": {}}, f)

    return jsonify({"bucket_id": bucket_id})


# Delete a bucket
@api_blueprint.route("/buckets/<bucket_id>", methods=["DELETE"])
def delete_bucket(bucket_id):
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    permissions = get_permissions(user, "SYSTEM")

    if permissions not in ["admin", "write"]:
        return jsonify({"error": "You do not have permission to delete a bucket"}), 403

    bucket_path = os.path.join(file_storage_location, bucket_id)

    if not os.path.exists(bucket_path):
        return jsonify({"error": "Bucket does not exist"}), 404

    # Delete the bucket from the FILESERVER_BUCKETS.fsconfig file
    
    # Wait for the buckets write lock to be released
    while os.path.exists(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig.lock")):
        time.sleep(0.1)

    # Create the buckets write lock
    with open(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig"), "r") as f:
        buckets = json.load(f)

    del buckets[bucket_id]

    with open(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig"), "w") as f:
        json.dump(buckets, f)

    # Release the buckets write lock
    os.remove(os.path.join(file_storage_location, "FILESERVER_BUCKETS.fsconfig.lock"))

    # Delete the bucket from the user's permissions

    # Wait for the permissions write lock to be released
    while os.path.exists(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock")):
        time.sleep(0.1)

    # Create the permissions write lock
    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "r") as f:
        permissions = json.load(f)

    permissions[user]["buckets"].remove(bucket_id)
    del permissions[user]["permissions"][bucket_id]

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "w") as f:
        json.dump(permissions, f)

    # Release the permissions write lock
    os.remove(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"))

    # Delete the bucket from the file storage location
    shutil.rmtree(bucket_path)

    return jsonify({"success": True})
    

# Get the list of files in a bucket
@api_blueprint.route("/buckets/<bucket_id>/files", methods=["GET"])
def get_files(bucket_id):
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    bucket_path = os.path.join(file_storage_location, bucket_id)

    if not os.path.exists(bucket_path):
        return jsonify({"error": "Bucket does not exist"}), 404
    
    permissions = get_permissions(user, bucket_id)

    if permissions not in ["admin", "read", "write"]:
        return jsonify({"error": "You do not have permission to get the list of files in this bucket"}), 403
    
    with open(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig"), "r") as f:
        bucket_config = json.load(f)

    file_data = []
    for file_id in bucket_config["files"]:
        file_data.append({
            "file_id": file_id,
            "file_name": bucket_config["files"][file_id]["file_name"],
            "file_size": bucket_config["files"][file_id]["file_size"],
            "created_by": bucket_config["files"][file_id]["created_by"],
            "created_at": bucket_config["files"][file_id]["created_at"]
        })


    return jsonify(file_data)

    
# Upload a file to a bucket
@api_blueprint.route("/buckets/<bucket_id>/files", methods=["POST"])
def upload_file(bucket_id):
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    bucket_path = os.path.join(file_storage_location, bucket_id)

    if not os.path.exists(bucket_path):
        return jsonify({"error": "Bucket does not exist"}), 404

    permissions = get_permissions(user, bucket_id)

    if permissions not in ["admin", "write"]:
        return jsonify({"error": "You do not have permission to upload a file to this bucket"}), 403

    file = request.files.get("file")

    if not file:
        return jsonify({"error": "No file provided"}), 400
    
    file_id = str(uuid.uuid4())
    while os.path.exists(os.path.join(bucket_path, file_id)):
        file_id = str(uuid.uuid4())

    file_name = file.filename

    file.stream.seek(0, 2)
    file_size = file.stream.tell()
    file_size_mb = file_size / (1024 * 1024)
    file.stream.seek(0)

    if file_size_mb > MAXIMUM_FILE_SIZE:
        return jsonify({"error": "File size is too large. Please limit the file size to " + str(MAXIMUM_FILE_SIZE) + "MB. Your file is " + str(int(file_size_mb)+1) + "MB."}), 413

    file_path = os.path.join(bucket_path, file_id)

    with open(file_path, "wb") as f:
        file.stream.seek(0)
        shutil.copyfileobj(file.stream, f)

    # Wait for the bucket config write lock to be released
    while os.path.exists(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig.lock")):
        time.sleep(0.1)

    # Create the bucket config write lock
    with open(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig"), "r") as f:
        bucket_config = json.load(f)

    bucket_config["files"][file_id] = {
        "file_name": file_name,
        "file_size": file_size_mb,
        "created_by": user,
        "created_at": datetime.now().isoformat()
    }

    with open(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig"), "w") as f:
        json.dump(bucket_config, f)

    # Release the bucket config write lock
    os.remove(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig.lock"))

    return jsonify({"file_id": file_id})


# Delete a file from a bucket
@api_blueprint.route("/buckets/<bucket_id>/files/<file_id>", methods=["DELETE"])
def delete_file(bucket_id, file_id):
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    bucket_path = os.path.join(file_storage_location, bucket_id)

    if not os.path.exists(bucket_path):
        return jsonify({"error": "Bucket does not exist"}), 404

    permissions = get_permissions(user, bucket_id)

    if permissions not in ["admin", "write"]:
        return jsonify({"error": "You do not have permission to delete a file from this bucket"}), 403
    
    file_path = os.path.join(bucket_path, file_id)

    if not os.path.exists(file_path):
        return jsonify({"error": "File does not exist"}), 404

    # Wait for the bucket config write lock to be released
    while os.path.exists(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig.lock")):
        time.sleep(0.1)

    # Create the bucket config write lock
    with open(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig"), "r") as f:
        bucket_config = json.load(f)

    del bucket_config["files"][file_id]

    with open(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig"), "w") as f:
        json.dump(bucket_config, f)

    # Release the bucket config write lock
    os.remove(os.path.join(bucket_path, "FILESERVER_BUCKET_CONFIG.fsconfig.lock"))

    # Delete the file from the file storage location
    os.remove(file_path)

    return jsonify({"success": True})

# Get a file from a bucket
@api_blueprint.route("/buckets/<bucket_id>/files/<file_id>", methods=["GET"])
def get_file(bucket_id, file_id):
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    bucket_path = os.path.join(file_storage_location, bucket_id)

    if not os.path.exists(bucket_path):
        return jsonify({"error": "Bucket does not exist"}), 404
    
    permissions = get_permissions(user, bucket_id)

    if permissions not in ["admin", "read", "write"]:
        return jsonify({"error": "You do not have permission to get this file"}), 403

    file_path = os.path.join(bucket_path, file_id)

    if not os.path.exists(file_path):
        return jsonify({"error": "File does not exist"}), 404
    
    # Get the file name
    with open(bucket_path + "/FILESERVER_BUCKET_CONFIG.fsconfig", "r") as f:
        bucket_config = json.load(f)

    file_name = bucket_config["files"][file_id]["file_name"]

    return send_file(file_path, as_attachment=True, download_name=file_name)
    

# Set the permission level for a user on a bucket
@api_blueprint.route("/buckets/<bucket_id>/permissions", methods=["POST"])
def set_permission(bucket_id):
    _user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    bucket_path = os.path.join(file_storage_location, bucket_id)

    if not os.path.exists(bucket_path):
        return jsonify({"error": "Bucket does not exist"}), 404

    permissions = get_permissions(user, bucket_id)

    if permissions not in ["admin"]:
        return jsonify({"error": "You do not have permission to set the permission level for this bucket"}), 403
    
    data = request.get_json()

    user = data["user"] if "user" in data else None
    permission = data["permission"] if "permission" in data else None

    if not user:
        return jsonify({"error": "User is required"}), 400

    if not permission:
        return jsonify({"error": "Permission is required"}), 400

    if permission not in ["admin", "read", "write", "remove"]:
        return jsonify({"error": "Invalid permission. Must be one of: admin, read, write, remove."}), 400

    # Wait for the permissions write lock to be released
    while os.path.exists(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock")):
        time.sleep(0.1)

    # Create the permissions write lock
    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "r") as f:
        permissions = json.load(f)

    if permission == "remove":
        if user in permissions and bucket_id in permissions[user]["permissions"]:
            del permissions[user]["permissions"][bucket_id]
        if user in permissions and bucket_id in permissions[user]["buckets"]:
            permissions[user]["buckets"].remove(bucket_id)
    else:

        if user not in permissions:
            permissions[user] = {
                "permissions": {},
                "buckets": []
            }

        permissions[user]["permissions"][bucket_id] = permission
        if bucket_id not in permissions[user]["buckets"]:
            permissions[user]["buckets"].append(bucket_id)

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "w") as f:
        json.dump(permissions, f)

    # Release the permissions write lock
    os.remove(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"))

    return jsonify({"success": True})


# Create a new system admin
@api_blueprint.route("/system/admins", methods=["POST"])
def create_system_admin():
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    permissions = get_permissions(user, "SYSTEM")

    if permissions not in ["admin"]:
        return jsonify({"error": "You do not have permission to create a new system admin"}), 403
    
    data = request.get_json()

    new_admin = data["admin"] if "admin" in data else None

    if not new_admin:
        return jsonify({"error": "New admin is required"}), 400
    
    # Wait for the permissions write lock to be released
    while os.path.exists(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock")):
        time.sleep(0.1)

    # Create the permissions write lock
    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "r") as f:
        permissions = json.load(f)

    if new_admin in permissions:
        permissions[new_admin]["permissions"]["SYSTEM"] = "admin"
        permissions[new_admin]["permissions"]["*"] = "admin"
        permissions[new_admin]["buckets"].append("*")
    else:
        permissions[new_admin] = {
            "permissions": {"SYSTEM": "admin", "*": "admin"},
            "buckets": ["*"]
        }

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "w") as f:
        json.dump(permissions, f)

    # Release the permissions write lock
    os.remove(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"))

    return jsonify({"success": True})
        
    
# Delete a system admin
@api_blueprint.route("/system/admins", methods=["DELETE"])
def delete_system_admin():
    user = verifyUser(request.headers.get('Authorization').split(" ")[1], file_storage_location)

    permissions = get_permissions(user, "SYSTEM")

    if permissions not in ["admin"]:
        return jsonify({"error": "You do not have permission to delete a system admin"}), 403
    
    # Get the admin to delete
    data = request.get_json()

    admin_to_delete = data["admin"] if "admin" in data else None

    if not admin_to_delete:
        return jsonify({"error": "Admin to delete is required"}), 400
    
    # Wait for the permissions write lock to be released
    while os.path.exists(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock")):
        time.sleep(0.1)

    # Create the permissions write lock
    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"), os.O_CREAT | os.O_EXCL) as f:
        f.write(user)

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "r") as f:
        permissions = json.load(f)

    if admin_to_delete in permissions:
        if "SYSTEM" in permissions[admin_to_delete]["permissions"]:
            del permissions[admin_to_delete]["permissions"]["SYSTEM"]
        if "*" in permissions[admin_to_delete]["permissions"]:
            del permissions[admin_to_delete]["permissions"]["*"]
        if "*" in permissions[admin_to_delete]["buckets"]:
            permissions[admin_to_delete]["buckets"].remove("*")
            

    with open(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig"), "w") as f:
        json.dump(permissions, f)

    # Release the permissions write lock
    os.remove(os.path.join(file_storage_location, "FILESERVER_PERMISSIONS.fsconfig.lock"))

    return jsonify({"success": True})
